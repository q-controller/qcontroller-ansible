QController Ansible Role
========================

An Ansible role to manage virtual machines using QController API.

Requirements
------------

- QController server running and accessible

**Note:** This role uses generated code from protobuf and OpenAPI specifications. To regenerate the code, run:

```bash
docker run --rm -it -v $(pwd):$(pwd) -w $(pwd) $(docker build -q .) $(pwd)/qcontroller/files/generated
```

Role Variables
--------------

### Required Variables

- `qcontroller_name`: Name of the virtual machine
- `qcontroller_state`: Desired state of the VM (present, running, stopped, absent)

### Optional Variables

- `qcontroller_image`: VM image to use (required when state is 'present' or 'running')
- `qcontroller_cpus`: Number of CPUs (default: 2)
- `qcontroller_memory`: Memory in MB (default: 2048)
- `qcontroller_disk`: Disk size in MB (default: 40960)
- `qcontroller_timeout`: Timeout in seconds for operations (default: 60)
- `qcontroller_force`: Force stop VM when stopping (default: false)
- `qcontroller_host`: QController server host (default: localhost)
- `qcontroller_port`: QController server port (default: 8080)

### Return Values

The role sets a fact `qcontroller_result` containing:
- `name`: VM name
- `state`: Current VM state
- `ipaddresses`: List of VM IP addresses
- `cpus`, `memory`, `disk`: VM resource configuration

Dependencies
------------

None

Example Playbook
----------------

```yaml
- hosts: localhost
  roles:
    - role: qcontroller
      vars:
        qcontroller_name: "my-vm"
        qcontroller_state: "running"
        qcontroller_image: "ubuntu-20.04"
        qcontroller_cpus: 4
        qcontroller_memory: 4096
```

Access VM information:
```yaml
- name: Show VM IP
  debug:
    msg: "VM IP: {{ qcontroller_result.ipaddresses[0] }}"
  when: qcontroller_result.ipaddresses | length > 0
```

License
-------

MIT-0

Author Information
------------------

Nikita Vakula
