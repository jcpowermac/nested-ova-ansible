#!/usr/bin/env python3
"""
Ansible filter plugin to convert OpenShift platform.yaml spec to vsphere_topology.yml format
"""


class FilterModule:
    """Ansible filter plugin for platform spec conversion"""

    def filters(self):
        return {
            'convert_platform_spec': self.convert_platform_spec,
            'extract_cluster_name': self.extract_cluster_name,
            'extract_datacenter_name': self.extract_datacenter_name
        }

    def convert_platform_spec(self, platform_spec):
        """
        Convert OpenShift platform.yaml format to new vsphere_topology.yml format

        Args:
            platform_spec: Dictionary containing platform.vsphere structure

        Returns:
            Dictionary in vsphere_topology.yml format
        """
        if not isinstance(platform_spec, dict):
            return {}

        vsphere_config = platform_spec.get('platform', {}).get('vsphere', {})
        if not vsphere_config:
            return {}

        # Initialize new topology structure
        topology = {
            'deployment': {
                'name': 'converted-deployment',
                'version': 'VC8.0.2.00100-22617221-ESXi8.0u2c'
            },
            'parent_vcenter': {
                'hostname': '${GOVC_URL}',
                'username': '${GOVC_USERNAME}',
                'password': '${GOVC_PASSWORD}',
                'datacenter': '${GOVC_DATACENTER}',
                'datastore': '${GOVC_DATASTORE}',
                'cluster': '${GOVC_CLUSTER}',
                'network': '${GOVC_NETWORK}',
                'folder': 'nested'
            },
            'resources': {
                'total_vcpus': 24,
                'total_memory_mb': 98304,
                'total_disk_gb': 1024,
                'hosts_per_failure_domain': 1
            },
            'nested_vcenters': []
        }

        # Group failure domains by vCenter
        vcenter_map = {}
        failure_domains = vsphere_config.get('failureDomains', [])

        for fd in failure_domains:
            server = fd.get('server')
            if not server:
                continue

            # Initialize vCenter entry if not exists
            if server not in vcenter_map:
                # Find matching vCenter from vcenters list
                vcenter_info = next(
                    (vc for vc in vsphere_config.get('vcenters', [])
                     if vc.get('server') == server),
                    {'server': server, 'user': 'administrator@vsphere.local'}
                )

                vcenter_map[server] = {
                    'name': server,
                    'credentials': {
                        'domain': 'vsphere.local',
                        'password': '{{ nested_vcenter_password }}'
                    },
                    'datacenters': []
                }

            # Extract topology information
            topology_info = fd.get('topology', {})
            dc_name = topology_info.get('datacenter', '')
            compute_cluster = topology_info.get('computeCluster', '')
            cluster_name = self.extract_cluster_name(compute_cluster)
            resource_pool = topology_info.get('resourcePool', '')
            pool_name = self.extract_cluster_name(resource_pool)

            # Find or create datacenter
            dc = next(
                (d for d in vcenter_map[server]['datacenters']
                 if d['name'] == dc_name),
                None
            )
            if not dc:
                dc = {
                    'name': dc_name,
                    'region': fd.get('region', dc_name),
                    'clusters': []
                }
                vcenter_map[server]['datacenters'].append(dc)

            # Determine zone type
            zone_type = 'HostGroup' if fd.get('zoneAffinity') == 'HostGroup' else 'ComputeCluster'

            # Extract networks
            networks = topology_info.get('networks', ['VM Network'])

            # Create cluster entry
            cluster = {
                'name': cluster_name,
                'zone': fd.get('zone', f"{dc_name}-{cluster_name}"),
                'zone_type': zone_type,
                'resource_pool': pool_name,
                'drs_enabled': True,
                'ha_enabled': True,
                'hosts_count': 1,
                'networks': networks,
                'datastores': []
            }

            # Add datastore information if available
            datastore_path = topology_info.get('datastore', '')
            if datastore_path:
                datastore_name = self.extract_cluster_name(datastore_path)
                # Check if it looks like NFS (common naming patterns)
                if 'nfs' in datastore_name.lower() or 'shared' in datastore_name.lower():
                    cluster['datastores'].append({
                        'type': 'nfs',
                        'name': datastore_name
                    })
                else:
                    cluster['datastores'].append({
                        'type': 'vmfs',
                        'name': datastore_name
                    })

            dc['clusters'].append(cluster)

        # Convert map to list
        topology['nested_vcenters'] = list(vcenter_map.values())

        return topology

    def extract_cluster_name(self, path):
        """
        Extract cluster name from vSphere path

        Args:
            path: vSphere path like /datacenter/host/cluster or /datacenter/host/cluster/Resources/pool

        Returns:
            Cluster or pool name
        """
        if not path:
            return ''

        # Remove leading/trailing slashes
        path = path.strip('/')

        # Split by slashes
        parts = path.split('/')

        # For paths like: datacenter/host/cluster
        # or: datacenter/host/cluster/Resources/pool
        if len(parts) >= 3:
            # If Resources exists, get everything after it
            if 'Resources' in parts:
                idx = parts.index('Resources')
                if idx + 1 < len(parts):
                    return parts[idx + 1]
            # Otherwise return the third part (cluster name)
            return parts[2]

        # Fallback: return last part
        return parts[-1] if parts else ''

    def extract_datacenter_name(self, path):
        """
        Extract datacenter name from vSphere path

        Args:
            path: vSphere path like /datacenter/host/cluster

        Returns:
            Datacenter name
        """
        if not path:
            return ''

        # Remove leading/trailing slashes
        path = path.strip('/')

        # Split by slashes
        parts = path.split('/')

        # Datacenter is typically the first part
        return parts[0] if parts else ''
