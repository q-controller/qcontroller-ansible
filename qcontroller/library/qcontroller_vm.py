import time
from typing import Any, Callable

from ansible.module_utils.basic import AnsibleModule
from controller_service import (
    ApiClient,
    Configuration,
    ControllerServiceApi,
    ServicesV1CreateRequest,
    ServicesV1Info,
    ServicesV1StartRequest,
    ServicesV1StopRequest,
    SettingsV1VM,
    VmStatemachineV1CloudInit,
)
from controller_service.exceptions import ServiceException
from image_service import ApiClient as ImageApiClient
from image_service import Configuration as ImageServiceConfiguration
from image_service import ImageServiceApi
from settings.v1.settings_pb2 import VM as Hardware
from vm.statemachine.v1.statemachine_pb2 import CloudInit, Instance, State


class Controller:
    api: ControllerServiceApi

    def __init__(self, host="localhost", port=8080):
        self.api = ControllerServiceApi(
            api_client=ApiClient(
                configuration=Configuration(
                    host=f"http://{host}:{port}",
                    ssl_ca_cert=None,
                    api_key=None,
                    api_key_prefix=None,
                )
            )
        )

    def get(self, instance_id: str) -> list[ServicesV1Info]:
        try:
            result = self.api.controller_service_info(name=instance_id)
            if result.info:
                return result.info
        except ServiceException as e:
            if e.status == 500:
                return []
            raise e

    def create(self, image: str, instance: Instance):
        return self.api.controller_service_create(
            services_v1_create_request=ServicesV1CreateRequest(
                vm=SettingsV1VM(
                    cpus=instance.hardware.cpus,
                    memory=instance.hardware.memory,
                    disk=instance.hardware.disk,
                ),
                name=instance.id,
                start=False,
                image=image,
                cloudInit=VmStatemachineV1CloudInit(
                    userdata=instance.cloudinit.userdata,
                    networkConfig=instance.cloudinit.network_config,
                ),
            )
        )

    def start(self, instance_id: str):
        return self.api.controller_service_start(
            name=instance_id,
            services_v1_start_request=ServicesV1StartRequest(name=instance_id),
        )

    def stop(self, instance_id: str, force: bool = False):
        return self.api.controller_service_stop(
            name=instance_id,
            services_v1_stop_request=ServicesV1StopRequest(
                name=instance_id, force=force
            ),
        )

    def delete(self, instance_id: str):
        return self.api.controller_service_remove(name=instance_id)


class ImageService:
    api: ImageServiceApi

    def __init__(self, host="localhost", port=8080):
        self.api = ImageServiceApi(
            api_client=ImageApiClient(
                configuration=ImageServiceConfiguration(
                    host=f"http://{host}:{port}",
                    ssl_ca_cert=None,
                    api_key=None,
                    api_key_prefix=None,
                )
            )
        )

    def upload_image(self, id: str, file_path: str, overwrite: bool = False) -> str:
        with open(file_path, "rb") as file:
            if not overwrite:
                existing_images = self.api.v1_images_get()
                for img in existing_images.images:
                    if img.image_id == id:
                        return img.image_id
            self.api.v1_images_post(id=id, file=file.read())
            return id


def get_ip_address(controller: Controller, instance_id: str) -> str:
    info = controller.get(instance_id)
    if info and info[0].ipaddresses:
        return info[0].ipaddresses[0]
    raise Exception("IP address not found")


def get_status(controller: Controller, instance_id: str) -> State:
    info = controller.get(instance_id)
    if info:
        state = State.Value(info[0].state)
        return state
    return State.STATE_UNSPECIFIED


def retry(
    func: Callable, max_retries: int = 3, interval: float = 1.0, *args, **kwargs
) -> Any:
    """
    Retry a function up to max_retries times, waiting interval seconds between attempts.
    Raises the last exception if all retries fail.
    """
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries:
                time.sleep(interval)
            else:
                raise


def serialize_vm_info(vm_info: ServicesV1Info) -> dict:
    """Serialize ServicesV1Info object to a dictionary"""
    return {
        "name": vm_info.name,
        "state": vm_info.state,
        "ipaddresses": vm_info.ipaddresses,
        "cpus": vm_info.details.cpus,
        "memory": vm_info.details.memory,
        "disk": vm_info.details.disk,
    }


def run_module():
    """Main Ansible module function"""

    module_args = dict(
        name=dict(type="str", required=True),
        image=dict(type="str"),
        file=dict(type="str"),
        cpus=dict(type="int"),
        memory=dict(type="int"),
        disk=dict(type="int"),
        cloud_init=dict(
            type="dict",
            options=dict(
                userdata=dict(type="str", required=False),
                network_config=dict(type="str", required=False),
            ),
        ),
        overwrite=dict(type="bool", required=False, default=False),
        force=dict(type="bool", required=False, default=False),
        state=dict(
            type="str",
            required=True,
            choices=["present", "running", "stopped", "absent"],
        ),
        timeout=dict(
            type="int", required=False, default=60
        ),  # duration in seconds, must be non-negative
        qcontroller_host=dict(type="str", required=False, default="localhost"),
        qcontroller_port=dict(type="int", required=False, default=8080),
    )

    result = dict(changed=False, message="", vm_info={})

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True,
        required_if=[
            ("state", "present", ["name", "image", "cpus", "memory", "disk"]),
            ("state", "running", ["name"]),
            ("state", "stopped", ["name"]),
            ("state", "absent", ["name"]),
        ],
    )

    params = module.params
    desired_state = params["state"]
    host = params["qcontroller_host"]
    port = params["qcontroller_port"]
    name = params["name"]
    timeout = params["timeout"]

    # Input validation
    if params.get("cpus") and params["cpus"] <= 0:
        module.fail_json(msg="Parameter 'cpus' must be greater than 0")

    if params.get("memory") and params["memory"] <= 0:
        module.fail_json(msg="Parameter 'memory' must be greater than 0")

    if params.get("disk") and params["disk"] <= 0:
        module.fail_json(msg="Parameter 'disk' must be greater than 0")

    if params.get("timeout") and params["timeout"] <= 0:
        module.fail_json(msg="Parameter 'timeout' must be greater than 0")

    create = False
    start = False
    stop = False
    delete = False
    try:
        controller = Controller(host=host, port=port)
        image_registry = ImageService(host=host, port=port)
        info = controller.get(name)
        msg = ""
        if desired_state == "present":
            msg = "VM successfully created"
            if not info:
                create = True
        elif desired_state == "running":
            msg = "VM successfully started"
            if not info:
                create = True
                start = True
            if info and State.Value(info[0].state) != State.STATE_RUNNING:
                start = True
        elif desired_state == "stopped":
            msg = "VM successfully stopped"
            if info and State.Value(info[0].state) != State.STATE_STOPPED:
                stop = True
        elif desired_state == "absent":
            msg = "VM successfully deleted"
            if info:
                if State.Value(info[0].state) != State.STATE_STOPPED:
                    stop = True
                delete = True

        if create:
            image = params["image"]
            file = params["file"]
            cpus = params["cpus"]
            memory = params["memory"]
            disk = params["disk"]
            cloud_init = params.get(
                "cloud_init",
                {
                    "userdata": "",
                    "network_config": "",
                },
            )
            if file:
                image = image_registry.upload_image(
                    image, file, params.get("overwrite", False)
                )
            controller.create(
                image=image,
                instance=Instance(
                    id=name,
                    hardware=Hardware(cpus=cpus, memory=memory, disk=disk),
                    cloudinit=CloudInit(
                        userdata=cloud_init.get("userdata", ""),
                        network_config=cloud_init.get("network_config", ""),
                    ),
                ),
            )
        if start:
            controller.start(name)
            retry(
                get_ip_address,
                max_retries=timeout // 2,
                interval=1,
                controller=controller,
                instance_id=name,
            )
        if stop:
            force = params["force"]
            controller.stop(name, force=force)

            def check_stopped():
                if get_status(controller, name) == State.STATE_STOPPED:
                    return State.STATE_STOPPED
                raise Exception("VM not stopped")

            retry(
                check_stopped,
                max_retries=timeout // 2,
                interval=1,
            )
        if delete:
            controller.delete(name)

        info = controller.get(name)
        result["changed"] = True
        result["message"] = msg
        if info:
            result["result"] = serialize_vm_info(info[0])
        else:
            result["result"] = {}
        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg=f"QController operation failed: {str(e)}", **result)


def main():
    run_module()


if __name__ == "__main__":
    main()
