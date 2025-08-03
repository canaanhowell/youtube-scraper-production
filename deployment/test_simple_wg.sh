#!/bin/bash

# Simple WireGuard test script

echo "Testing WireGuard connection..."

# Create WireGuard config
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = 6KFmgM+5j6xlQdRDX1z0XRF889eXooyUHnCLlVn4lW8=
Address = 10.14.0.2/16

[Peer]
PublicKey = Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk=
AllowedIPs = 0.0.0.0/0
Endpoint = 84.17.35.107:51820
PersistentKeepalive = 25
EOF

chmod 600 /etc/wireguard/wg0.conf

# Start WireGuard manually
echo "Creating interface..."
ip link add dev wg0 type wireguard

echo "Configuring interface..."
wg setconf wg0 /etc/wireguard/wg0.conf

echo "Setting IP address..."
ip address add 10.14.0.2/16 dev wg0

echo "Bringing interface up..."
ip link set up dev wg0

echo "Adding route..."
ip route add default dev wg0 table 51820
ip rule add not fwmark 51820 table 51820
wg set wg0 fwmark 51820

echo "Waiting for connection..."
sleep 5

echo "Testing connection..."
curl -s --max-time 10 https://ipinfo.io/json || echo "Connection failed"

echo "Cleaning up..."
ip link del wg0
ip rule del table 51820
ip route flush table 51820

echo "Done!"