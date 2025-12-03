#!/usr/bin/env python3
"""
Convert legacy platform.yaml format to new vsphere_topology.yml format

This script converts the OpenShift-specific platform.yaml format used in v1
to the new deployment-focused vsphere_topology.yml format in v2.

Usage:
    ./convert_topology.py platform.yaml > vsphere_topology.yml
    ./convert_topology.py platform.yaml -o vsphere_topology.yml
"""

import argparse
import sys
import yaml
from typing import Dict, List, Any


class TopologyConverter:
    """Convert platform.yaml to vsphere_topology.yml format"""

    def __init__(self, platform_spec: Dict[str, Any]):
        self.platform_spec = platform_spec
        self.topology = {
            'deployment_name': 'nested-vsphere',
            'region': 'region-1',
            'esxi_hosts': [],
            'vcenter_vms': [],
            'failure_domains': [],
            'content_library': {}
        }

    def convert(self) -> Dict[str, Any]:
        """Main conversion logic"""
        self._extract_basic_info()
        self._extract_esxi_hosts()
        self._extract_vcenter_vms()
        self._extract_failure_domains()
        return self.topology

    def _extract_basic_info(self):
        """Extract deployment name and region"""
        vsphere = self.platform_spec.get('platform', {}).get('vsphere', {})

        # Try to infer deployment name from cluster
        if 'cluster' in vsphere:
            cluster_name = vsphere['cluster']
            # Remove common prefixes/suffixes
            deployment_name = cluster_name.replace('_cluster', '').replace('-cluster', '')
            self.topology['deployment_name'] = deployment_name

        # Extract region if defined
        failure_domains = vsphere.get('failureDomains', [])
        if failure_domains and len(failure_domains) > 0:
            first_fd = failure_domains[0]
            if 'region' in first_fd.get('topology', {}):
                self.topology['region'] = first_fd['topology']['region']

    def _extract_esxi_hosts(self):
        """Extract ESXi host definitions from nestedhostsv2"""
        nested_hosts = self.platform_spec.get('nestedhostsv2', {})

        for host_key, host_data in nested_hosts.items():
            if not isinstance(host_data, dict):
                continue

            esxi_host = {
                'name': host_data.get('vmnameesxi', host_key),
                'ip': host_data.get('ipesxi'),
                'mask': host_data.get('nmesxi', '255.255.255.0'),
                'gw': host_data.get('gw'),
                'vlan': host_data.get('vlan'),
                'cpu': host_data.get('cpu_esxi', 8),
                'memory_mb': host_data.get('ram_esxi', 65536),
                'disk_gb': host_data.get('disk_esxi', 200),
                'nested_hv': host_data.get('nested', True),
                'username': 'root',
                'password': host_data.get('esxi_password', 'VMware1!'),
                'datacenter': host_data.get('datacenter', 'dc1'),
                'cluster': host_data.get('cluster', 'cluster1'),
                'folder': host_data.get('folder_esxi', '/'),
                'parent_resource_pool': host_data.get('resource_pool_esxi', ''),
                'parent_host': host_data.get('host_esxi', ''),
                'parent_datastore': host_data.get('datastore_esxi', '')
            }

            # Remove empty values
            esxi_host = {k: v for k, v in esxi_host.items() if v not in [None, '', []]}

            self.topology['esxi_hosts'].append(esxi_host)

    def _extract_vcenter_vms(self):
        """Extract vCenter VM definitions"""
        vcenter_data = self.platform_spec.get('vcenter', {})

        if not vcenter_data:
            return

        vcenter_vm = {
            'name': vcenter_data.get('vmname', 'vcsa'),
            'hostname': vcenter_data.get('ip'),
            'ip': vcenter_data.get('ip'),
            'mask': vcenter_data.get('mask', '255.255.255.0'),
            'gw': vcenter_data.get('gw'),
            'dns': vcenter_data.get('dns', '8.8.8.8'),
            'domain': vcenter_data.get('domain', 'lab.local'),
            'ntp': vcenter_data.get('ntp', 'pool.ntp.org'),
            'cpu': vcenter_data.get('cpu', 8),
            'memory_mb': vcenter_data.get('ram', 24576),
            'disk_gb': vcenter_data.get('disk', 250),
            'username': vcenter_data.get('user', 'administrator@vsphere.local'),
            'password': vcenter_data.get('password', 'VMware1!'),
            'sso_domain': vcenter_data.get('sso_domain', 'vsphere.local'),
            'datacenter': vcenter_data.get('datacenter', 'dc1'),
            'folder': vcenter_data.get('folder', '/'),
            'parent_resource_pool': vcenter_data.get('resource_pool', ''),
            'parent_host': vcenter_data.get('host', ''),
            'parent_datastore': vcenter_data.get('datastore', ''),
            'datacenters': self._extract_datacenter_config(vcenter_data),
            'dvswitches': self._extract_dvswitch_config(vcenter_data),
            'esxi_hosts': self._map_esxi_to_vcenter()
        }

        # Remove empty values
        vcenter_vm = {k: v for k, v in vcenter_vm.items() if v not in [None, '', []]}

        self.topology['vcenter_vms'].append(vcenter_vm)

    def _extract_datacenter_config(self, vcenter_data: Dict) -> List[Dict]:
        """Extract datacenter and cluster configuration"""
        vsphere = self.platform_spec.get('platform', {}).get('vsphere', {})

        datacenter_name = vcenter_data.get('datacenter', 'dc1')
        cluster_name = vsphere.get('cluster', self._extract_cluster_name())

        datacenter = {
            'name': datacenter_name,
            'clusters': [{
                'name': cluster_name,
                'drs_enabled': True,
                'drs_vmotion_rate': 3,
                'ha_enabled': True,
                'ha_admission_control': True
            }]
        }

        return [datacenter]

    def _extract_dvswitch_config(self, vcenter_data: Dict) -> List[Dict]:
        """Extract distributed vSwitch configuration"""
        dvs_data = self.platform_spec.get('dvs', {})

        if not dvs_data:
            return []

        dvswitch = {
            'name': dvs_data.get('name', 'dvSwitch'),
            'datacenter': vcenter_data.get('datacenter', 'dc1'),
            'version': dvs_data.get('version', '7.0.0'),
            'mtu': dvs_data.get('mtu', 1500),
            'uplinks': dvs_data.get('uplinks', 2),
            'discovery_protocol': dvs_data.get('discovery_protocol', 'lldp'),
            'discovery_operation': dvs_data.get('discovery_operation', 'listen'),
            'port_groups': self._extract_port_groups(dvs_data)
        }

        return [dvswitch]

    def _extract_port_groups(self, dvs_data: Dict) -> List[Dict]:
        """Extract port group configuration"""
        port_groups = []

        pg_data = dvs_data.get('portgroups', [])
        for pg in pg_data:
            if isinstance(pg, dict):
                port_group = {
                    'name': pg.get('name'),
                    'vlan': pg.get('vlan'),
                    'num_ports': pg.get('ports', 128)
                }
                port_groups.append(port_group)

        return port_groups

    def _extract_cluster_name(self) -> str:
        """Extract cluster name from various sources"""
        vsphere = self.platform_spec.get('platform', {}).get('vsphere', {})

        # Try direct cluster field
        if 'cluster' in vsphere:
            return vsphere['cluster']

        # Try to extract from failure domains
        failure_domains = vsphere.get('failureDomains', [])
        if failure_domains and len(failure_domains) > 0:
            first_fd = failure_domains[0]
            if 'computeCluster' in first_fd.get('topology', {}):
                return first_fd['topology']['computeCluster'].split('/')[-1]

        return 'cluster1'

    def _map_esxi_to_vcenter(self) -> List[Dict]:
        """Map ESXi hosts to vCenter configuration"""
        esxi_hosts = []

        for esxi in self.topology['esxi_hosts']:
            esxi_mapping = {
                'hostname': esxi['ip'],
                'username': esxi.get('username', 'root'),
                'password': esxi.get('password', 'VMware1!'),
                'datacenter': esxi.get('datacenter', 'dc1'),
                'cluster': esxi.get('cluster', 'cluster1')
            }
            esxi_hosts.append(esxi_mapping)

        return esxi_hosts

    def _extract_failure_domains(self):
        """Extract failure domain configuration"""
        vsphere = self.platform_spec.get('platform', {}).get('vsphere', {})
        failure_domains = vsphere.get('failureDomains', [])

        for fd_data in failure_domains:
            topology = fd_data.get('topology', {})

            failure_domain = {
                'name': fd_data.get('name', 'fd1'),
                'region': topology.get('region', self.topology['region']),
                'zone': topology.get('zone', fd_data.get('name', 'zone-a')),
                'zone_type': self._determine_zone_type(topology),
                'datacenter': topology.get('datacenter', 'dc1'),
                'cluster': self._extract_cluster_from_topology(topology)
            }

            # Add HostGroup-specific configuration
            if failure_domain['zone_type'] == 'HostGroup':
                failure_domain['hosts'] = self._extract_hosts_for_fd(fd_data)

            # Add datastore configuration
            if 'datastore' in topology:
                failure_domain['datastores'] = [topology['datastore'].split('/')[-1]]

            self.topology['failure_domains'].append(failure_domain)

    def _determine_zone_type(self, topology: Dict) -> str:
        """Determine zone type from topology"""
        if 'hostGroup' in topology:
            return 'HostGroup'
        elif 'computeCluster' in topology:
            return 'ComputeCluster'
        else:
            return 'ComputeCluster'

    def _extract_cluster_from_topology(self, topology: Dict) -> str:
        """Extract cluster name from topology"""
        if 'computeCluster' in topology:
            return topology['computeCluster'].split('/')[-1]
        return 'cluster1'

    def _extract_hosts_for_fd(self, fd_data: Dict) -> List[str]:
        """Extract host list for HostGroup zone type"""
        # This is a best-effort extraction
        # In v1, hosts were often hardcoded or derived from other sources
        # Return empty list - users will need to populate manually
        return []


def main():
    parser = argparse.ArgumentParser(
        description='Convert platform.yaml to vsphere_topology.yml',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Output to stdout
  %(prog)s platform.yaml

  # Output to file
  %(prog)s platform.yaml -o vsphere_topology.yml

  # Pretty print with comments
  %(prog)s platform.yaml --pretty
        """
    )
    parser.add_argument(
        'input_file',
        help='Input platform.yaml file'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output file (default: stdout)',
        default=None
    )
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Add comments and formatting to output'
    )

    args = parser.parse_args()

    # Load input file
    try:
        with open(args.input_file, 'r') as f:
            platform_spec = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert
    converter = TopologyConverter(platform_spec)
    topology = converter.convert()

    # Add header comment if pretty mode
    output = ""
    if args.pretty:
        output += "# Converted from platform.yaml by convert_topology.py\n"
        output += "# Review and adjust as needed, especially:\n"
        output += "#   - ESXi host passwords\n"
        output += "#   - vCenter credentials\n"
        output += "#   - Resource allocations\n"
        output += "#   - HostGroup host lists (if using HostGroup zone_type)\n\n"

    # Convert to YAML
    output += yaml.dump(topology, default_flow_style=False, sort_keys=False, indent=2)

    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Converted topology written to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
