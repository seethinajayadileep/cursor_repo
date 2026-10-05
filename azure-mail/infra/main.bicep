@description('Azure region for the VM and networking. Email resources are global.')
param location string = resourceGroup().location

@description('ACS / Email data residency')
param dataLocation string = 'United States'

@description('Linux admin username')
param adminUsername string = 'azureuser'

@description('SSH public key for azureuser')
param adminPublicKey string

@description('Size. B2ms = 8 GB, required for Mailcow.')
param vmSize string = 'Standard_B2ms'

@description('OS disk GB for mail storage')
param osDiskSizeGB int = 128

var suffix = uniqueString(resourceGroup().id)
var vnetName = 'vnet-mail-${suffix}'
var nsgName = 'nsg-mail-${suffix}'
var pipName = 'pip-mail-${suffix}'
var nicName = 'nic-mail-${suffix}'
var vmName = 'vm-mailcow'
var emailServiceName = take('email${suffix}', 24)
var acsName = take('acsmail${suffix}', 24)
var dnsLabel = take('mail${suffix}', 24)

resource nsg 'Microsoft.Network/networkSecurityGroups@2023-09-01' = {
  name: nsgName
  location: location
  properties: {
    securityRules: [
      { name: 'ssh', properties: { priority: 1000, access: 'Allow', direction: 'Inbound', protocol: 'Tcp', sourcePortRange: '*', destinationPortRange: '22', sourceAddressPrefix: '*', destinationAddressPrefix: '*' } }
      { name: 'smtp-in', properties: { priority: 1010, access: 'Allow', direction: 'Inbound', protocol: 'Tcp', sourcePortRange: '*', destinationPortRange: '25', sourceAddressPrefix: '*', destinationAddressPrefix: '*' } }
      { name: 'http', properties: { priority: 1020, access: 'Allow', direction: 'Inbound', protocol: 'Tcp', sourcePortRange: '*', destinationPortRange: '80', sourceAddressPrefix: '*', destinationAddressPrefix: '*' } }
      { name: 'https', properties: { priority: 1030, access: 'Allow', direction: 'Inbound', protocol: 'Tcp', sourcePortRange: '*', destinationPortRange: '443', sourceAddressPrefix: '*', destinationAddressPrefix: '*' } }
      { name: 'smtps', properties: { priority: 1040, access: 'Allow', direction: 'Inbound', protocol: 'Tcp', sourcePortRange: '*', destinationPortRange: '465', sourceAddressPrefix: '*', destinationAddressPrefix: '*' } }
      { name: 'submission', properties: { priority: 1050, access: 'Allow', direction: 'Inbound', protocol: 'Tcp', sourcePortRange: '*', destinationPortRange: '587', sourceAddressPrefix: '*', destinationAddressPrefix: '*' } }
      { name: 'imap', properties: { priority: 1060, access: 'Allow', direction: 'Inbound', protocol: 'Tcp', sourcePortRange: '*', destinationPortRange: '143', sourceAddressPrefix: '*', destinationAddressPrefix: '*' } }
      { name: 'imaps', properties: { priority: 1070, access: 'Allow', direction: 'Inbound', protocol: 'Tcp', sourcePortRange: '*', destinationPortRange: '993', sourceAddressPrefix: '*', destinationAddressPrefix: '*' } }
    ]
  }
}

resource vnet 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: { addressPrefixes: ['10.20.0.0/16'] }
    subnets: [
      {
        name: 'snet-mail'
        properties: {
          addressPrefix: '10.20.0.0/24'
          networkSecurityGroup: { id: nsg.id }
        }
      }
    ]
  }
}

resource pip 'Microsoft.Network/publicIPAddresses@2023-09-01' = {
  name: pipName
  location: location
  sku: { name: 'Standard' }
  properties: {
    publicIPAllocationMethod: 'Static'
    dnsSettings: {
      domainNameLabel: dnsLabel
    }
  }
}

resource nic 'Microsoft.Network/networkInterfaces@2023-09-01' = {
  name: nicName
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: { id: vnet.properties.subnets[0].id }
          privateIPAllocationMethod: 'Dynamic'
          publicIPAddress: { id: pip.id }
        }
      }
    ]
    networkSecurityGroup: { id: nsg.id }
  }
}

resource vm 'Microsoft.Compute/virtualMachines@2024-03-01' = {
  name: vmName
  location: location
  properties: {
    hardwareProfile: { vmSize: vmSize }
    osProfile: {
      computerName: vmName
      adminUsername: adminUsername
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: adminPublicKey
            }
          ]
        }
      }
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: '0001-com-ubuntu-server-jammy'
        sku: '22_04-lts-gen2'
        version: 'latest'
      }
      osDisk: {
        name: '${vmName}-os'
        createOption: 'FromImage'
        diskSizeGB: osDiskSizeGB
        managedDisk: { storageAccountType: 'Premium_LRS' }
      }
    }
    networkProfile: {
      networkInterfaces: [
        { id: nic.id }
      ]
    }
  }
}

resource emailService 'Microsoft.Communication/emailServices@2023-06-01' = {
  name: emailServiceName
  location: 'global'
  properties: {
    dataLocation: dataLocation
  }
}

resource azureManagedDomain 'Microsoft.Communication/emailServices/domains@2023-06-01' = {
  parent: emailService
  name: 'AzureManagedDomain'
  location: 'global'
  properties: {
    domainManagement: 'AzureManaged'
    userEngagementTracking: 'Disabled'
  }
}

resource acs 'Microsoft.Communication/communicationServices@2023-06-01' = {
  name: acsName
  location: 'global'
  properties: {
    dataLocation: dataLocation
  }
}

output publicIP string = pip.properties.ipAddress
output publicDnsName string = pip.properties.dnsSettings.fqdn
output sshUser string = adminUsername
output vmName string = vm.name
output publicIpName string = pip.name
output acsName string = acs.name
output acsId string = acs.id
output emailServiceName string = emailService.name
output emailServiceId string = emailService.id
output managedDomainId string = azureManagedDomain.id
output nsgName string = nsg.name
