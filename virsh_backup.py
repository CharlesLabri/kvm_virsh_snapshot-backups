#!/bin/python3
# CiC 2/2018

# ********* Imports *********
import subprocess
import re
import os 
import logging
from pathlib import Path

# ********* logging configuration *********
logging.basicConfig(filename='/var/log/vhost-backup.log',level=logging.DEBUG,format='%(asctime)s %(message)s')

# ********* Variables *********
globalServer = "REMOTEHOST"
globalPath = "/REMOTEMOUNT/"
globalUser = "USERNAME"
globalPassword = "PASSWORD"
globalDomain = "DOMAIN"
globalMount = "/mnt/" + globalServer + '/'
globalVMPath = "/LOCALVMPATH/"
globalExtension = "sn"
globalVMDict = {}


# ********* Functions *********
def gatherVMData():
	'''
		Gather the VM names from virsh that are on the system and add them to vmlist
	'''
	vmList = []
	storageList = []
	localVMDict = {}

	with subprocess.Popen(["virsh list --all --name"], stdout=subprocess.PIPE, shell=True) as proc:
	    vmList.extend(((proc.stdout.read()).decode('UTF-8')).split())

	for i in vmList:
		with subprocess.Popen("virsh domblklist {0}".format(i),stdout=subprocess.PIPE, shell=True, universal_newlines=True) as proc:
			for line in proc.stdout:
				if globalVMPath in line:
					device = (re.search(r"[vh]d[a-z] *(.*)", line)).group(1)
					storageList.append(device)
				else:
					pass

	for name in vmList:
		i = 0
		for storage in storageList:
			if name in storage:
				i = i+1
				storageDict = {i:storage}
				try:
					localVMDict[name].update(storageDict)
				except KeyError as e:
					localVMDict[name] = storageDict
	return(localVMDict)


def createPath(path):
	'''
		Check if the argument path exists.
		If it doesnt, create it.
	'''
	mountpath = Path(path)	
	if mountpath.is_dir() == True:
		logging.debug("Mount path already exists")
	else:
		os.mkdir(path)
		logging.debug("Created the mount path")

def mountPath(server, path, localpath, user, password, domain):
	'''
		mount the path passed in the arguments
	'''
	logging.debug("Mounting {0}".format(localpath))
	with subprocess.Popen("mount.cifs //{0}{1} {2} -o user={3},pass={4},dom={5},rw,vers=2.0".format(server, path, localpath, user, password, domain), stdout=subprocess.PIPE, shell=True) as proc:
		#need to add error handling here
		pass
	logging.debug("Mounted {0}".format(localpath))

def unMountPath(path):
	'''
		unmount the path passed in the argument
	'''
	logging.debug("going to unmount {0}".format(path))
	with subprocess.Popen("umount {0}".format(path), stdout=subprocess.PIPE, shell=True) as proc:
		pass
	logging.debug("umnounted {0}".format(path))

def backupVM(vmpath, vmname, vmdiskpath, backuppath, extension):
	'''
		will backup the passed VM with the vmname variable
	'''
	snapshotBool = Path(vmpath+vmname+'.'+extension)
	splitvmdiskpath = vmdiskpath.split('.')
	snapshot = splitvmdiskpath[0]+'.'+extension
	# logging.debug(vmpath,vmname,vmdiskpath,backuppath,extension,snapshot)

	logging.debug('***************************************')

	if snapshotBool.is_file():
		logging.debug("Already a snapshot of {0}".format(vmname))
		pass
	else:
		#take snapshot
		logging.debug("Going to snapshot single-disk VM: {0}".format(vmname))
		with subprocess.Popen("virsh snapshot-create-as --domain {0} --name {1} --disk-only --atomic".format(vmname, extension),stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...snapshot complete for: {0}".format(vmname))
		
		# rsync disk to backup server
		logging.debug("Going to rsync: {0} to: {1}".format(vmdiskpath, backuppath))
		with subprocess.Popen("rsync -q --inplace {0} {2}{1}.qcow2".format(vmdiskpath,vmname,backuppath),stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...rsync to {0} complete for disk: {1}".format(backuppath, vmdiskpath))

		# commit snapshot back to machine
		logging.debug("Going to commit disk: {0} back to: {1}".format(snapshot, vmname))
		with subprocess.Popen("virsh blockcommit --domain {0} --path {1} --active --pivot".format(vmname,snapshot), stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...commit of disk: {0} complete back to VM: {1}".format(snapshot, vmname))

		# delete metadata/snapshot from vm
		logging.debug("Going to delete the snapshot metadata for: {0}".format(vmname))
		with subprocess.Popen("virsh snapshot-delete --domain {0} --metadata {1}".format(vmname, extension), stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...metadata/snapshot deleted from: {0}".format(vmname))

		# delete the leftover snapshot file
		logging.debug("deleting the snapshot file: {0}".format(snapshot))
		with subprocess.Popen("rm -f {0}".format(snapshot), stdout=subprocess.PIPE, shell=True) as proc:
			pass	
		logging.debug("...deleted snapshot file: {}".format(snapshot))

		#dump the XML of the vm
		logging.debug("exporting VM configuration for: {0}".format(vmname))
		with subprocess.Popen("virsh dumpxml {0} > {1}{0}.xml".format(vmname, backuppath), stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...VM configuration exported for: {0} to {1}".format(vmname, backuppath))

def backupMultiDiskVM(vmpath, vmname, vmdiskpath, backuppath, extension):
	'''
		will backup the passed VM with the vmname variable, supports 2 disks without modification
	'''
	snapshotBool = Path(vmpath+vmname+'.'+extension)
	SplitVMDisk1 = vmdiskpath[1].split('.')
	SplitVMDisk2 = vmdiskpath[2].split('.')
	snapshot1 = SplitVMDisk1[0]+'.'+extension
	snapshot2 = SplitVMDisk2[0]+'.'+extension

	logging.debug('***************************************')

	if snapshotBool.is_file():
		logging.debug("Already a snapshot of {0}".format(vmname))
		pass
	else:
		#take snapshot
		logging.debug("Going to snapshot multi-disk VM: {0}".format(vmname))
		with subprocess.Popen("virsh snapshot-create-as --domain {0} --name {1} --disk-only --atomic".format(vmname, extension),stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...snapshot complete for: {0}".format(vmname))
		
		# rsync disk1 to backup server
		logging.debug("Going to rsync: {0} to: {1}".format(vmdiskpath[1], backuppath))
		with subprocess.Popen("rsync -q --inplace {0} {2}{1}.qcow2".format(vmdiskpath[1],vmname,backuppath),stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...rsync to {0} complete for disk: {1}".format(backuppath, vmdiskpath[1]))

		# rsync disk2 to backup server
		logging.debug("Going to rsync: {0} to: {1}".format(vmdiskpath[2], backuppath))
		with subprocess.Popen("rsync -q --inplace {0} {2}{1}.qcow2".format(vmdiskpath[2],vmname,backuppath),stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...rsync to {0} complete for server {1}".format(backuppath, vmdiskpath[2]))
		
		# commit snapshot1 back to machine
		logging.debug("Going to commit disk: {0} back to: {1}".format(snapshot1, vmname))
		with subprocess.Popen("virsh blockcommit --domain {0} --path {1} --active --pivot".format(vmname,snapshot1), stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...commit of disk: {0} complete back to server {1}".format(snapshot1, vmname))

		# commit snapshot2 back to machine
		logging.debug("Going to commit disk: {0} back to: {1}".format(snapshot2, vmname))
		with subprocess.Popen("virsh blockcommit --domain {0} --path {1} --active --pivot".format(vmname,snapshot2), stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...commit of disk: {0} complete back to VM {1}".format(snapshot2, vmname))

		# delete metadata/snapshot from vm
		logging.debug("Going to delete the snapshot metadata for: {0}".format(vmname))
		with subprocess.Popen("virsh snapshot-delete --domain {0} --metadata {1}".format(vmname, extension), stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...metadata/snapshot deleted from: {0}".format(vmname))

		# delete the leftover snapshot1 file
		logging.debug("Deleting the snapshot file: {0}".format(snapshot1))
		with subprocess.Popen("rm -f {0}".format(snapshot1), stdout=subprocess.PIPE, shell=True) as proc:
			pass	
		logging.debug("...deleted snapshot file: {0}".format(snapshot1))

		# delete the leftover snapshot2 file
		logging.debug("Deleting the snapshot file: {0}".format(snapshot2))
		with subprocess.Popen("rm -f {0}".format(snapshot2), stdout=subprocess.PIPE, shell=True) as proc:
			pass	
		logging.debug("...deleted snapshot file: {0}".format(snapshot2))

		#dump the XML of the vm
		logging.debug("Exporting VM configuration for: {0}".format(vmname))
		with subprocess.Popen("virsh dumpxml {0} > {1}{0}.xml".format(vmname, backuppath), stdout=subprocess.PIPE, shell=True) as proc:
			pass
		logging.debug("...VM configuration exported for: {0} to {1}".format(vmname, backuppath))

# ********* Runtume *********
globalVMDict = gatherVMData()

createPath(globalMount)
mountPath(globalServer, globalPath, globalMount, globalUser, globalPassword, globalDomain)


for k, v in globalVMDict.items():
	vList = globalVMDict[k]
	if len(vList) > 1:
		backupMultiDiskVM(globalVMPath, k, v, globalMount, globalExtension)
	else:
		for ksub,vsub in v.items():
			backupVM(globalVMPath, k, vsub, globalMount, globalExtension)

unMountPath(globalMount)
		
# ********* JUNK GOES BELOW HERE *********

