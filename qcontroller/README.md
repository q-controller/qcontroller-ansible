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

- `vm_name`: Name of the virtual machine
- `vm_state`: Desired state of the VM (present, running, stopped, absent)

### Optional Variables

- `vm_image`: VM image to use (required when state is 'present' or 'running')
- `vm_cpus`: Number of CPUs (default: 2)
- `vm_memory`: Memory in MB (default: 2048)
- `vm_disk`: Disk size in MB (default: 40960)
- `vm_timeout`: Timeout in seconds for operations (default: 60)
- `vm_force`: Force stop VM when stopping (default: false)
- `qcontroller_host`: QController server host (default: localhost)
- `qcontroller_port`: QController server port (default: 8080)

### Return Values

The role sets a fact `vm_result` containing:
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
        vm_name: "my-vm"
        vm_state: "running"
        vm_image: "ubuntu-20.04"
        vm_cpus: 4
        vm_memory: 4096
```

Access VM information:
```yaml
- name: Show VM IP
  debug:
    msg: "VM IP: {{ vm_result.ipaddresses[0] }}"
  when: vm_result.ipaddresses | length > 0
```

License
-------

MIT-0

Author Information
------------------

Nikita Vakula
