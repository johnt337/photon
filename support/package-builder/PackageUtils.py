from CommandUtils import CommandUtils
from Logger import Logger
import os
import shutil
from constants import constants
import re


class PackageUtils(object):
    
    def __init__(self,logName=None,logPath=None):
        if logName is None:
            self.logName = "PackageUtils"
        if logPath is None:
            logPath = constants.logPath
        self.logName=logName
        self.logPath=logPath
        self.logger=Logger.getLogger(logName,logPath)
        self.runInChrootCommand="./run-in-chroot.sh"
        self.rpmBinary = "rpm"
        self.installRPMPackageOptions = "-Uvh"
        self.nodepsRPMPackageOptions = "--nodeps"
        
        self.rpmbuildBinary = "rpmbuild"
        self.rpmbuildBuildallOption = "-ba"
        self.rpmbuildNocheckOption = "--nocheck"
        self.queryRpmPackageOptions = "-qa"
        self.forceRpmPackageOptions = "--force"
    
    def getRPMDestDir(self,rpmName,rpmDir):
        arch=""
        if rpmName.find("x86_64") != -1:
            arch='x86_64'
        elif rpmName.find("noarch") != -1:
            arch="noarch"
        rpmDestDir=rpmDir+"/"+arch
        return rpmDestDir
    
    def copyRPM(self,rpmFile,destDir):
        cmdUtils = CommandUtils()
        rpmName=os.path.basename(rpmFile)
        rpmDestDir=self.getRPMDestDir(rpmName,destDir)
        if not os.path.isdir(rpmDestDir):
            cmdUtils.runCommandInShell("mkdir -p "+rpmDestDir)
        rpmDestPath=rpmDestDir+"/"+rpmName
        shutil.copyfile(rpmFile,  rpmDestPath)
        return rpmDestPath
    
    def installRPM(self,package,chrootID,noDeps=False,destLogPath=None):
        self.logger.info("Installing rpm for package:"+package)
        self.logger.debug("No deps:"+str(noDeps))
        
        rpmfile=self.findRPMFileForGivenPackage(package)
        if rpmfile is None:
            self.logger.error("No rpm file found for package:"+package)
            raise Exception("Missing rpm file")

        rpmDestFile = self.copyRPM(rpmfile, chrootID+constants.topDirPath+"/RPMS")
        rpmFile=rpmDestFile.replace(chrootID,"")
        chrootCmd=self.runInChrootCommand+" "+chrootID
        logFile=chrootID+constants.topDirPath+"/LOGS"+"/"+package+".completed"
        
        rpmInstallcmd=self.rpmBinary+" "+ self.installRPMPackageOptions
        if noDeps:
            rpmInstallcmd+=" "+self.nodepsRPMPackageOptions
        rpmInstallcmd+=" "+rpmFile
        
        cmdUtils = CommandUtils()
        returnVal = cmdUtils.runCommandInShell(rpmInstallcmd, logFile, chrootCmd)
        if destLogPath is not None:
            shutil.copy2(logFile, destLogPath)
        if not returnVal:
            self.logger.error("Unable to install rpm:"+ rpmFile)
            raise Exception("RPM installation failed")
    
    def copySourcesTobuildroot(self,listSourceFiles,package,destDir):
        cmdUtils = CommandUtils()
        for source in listSourceFiles:
            sourcePath = cmdUtils.findFile(source,constants.sourcePath)
            if sourcePath is None or len(sourcePath) == 0:
                sourcePath = cmdUtils.findFile(source,constants.specPath)
            if sourcePath is None or len(sourcePath) == 0:
                self.logger.error("Missing source: "+source+". Cannot find sources for package: "+package)
                raise Exception("Missing source")
            if len(sourcePath) > 1:
                self.logger.error("Multiple sources found for source:"+source+"\n"+ ",".join(sourcePath) +"\nUnable to determine one.")
                raise Exception("Multiple sources found")
            self.logger.info("Copying... Source path :" + source + " Source filename: " + sourcePath[0])
            shutil.copy2(sourcePath[0],  destDir)
    
    def buildRPMSForGivenPackage(self,package, chrootID,destLogPath=None):
        self.logger.info("Building rpm's for package:"+package)

        listSourcesFiles = constants.specData.getSources(package)
        listPatchFiles =  constants.specData.getPatches(package)
        specFile = constants.specData.getSpecFile(package)
        specName = constants.specData.getSpecName(package) + ".spec"
        
        chrootSourcePath=chrootID+constants.topDirPath+"/SOURCES/"
        chrootSpecPath=constants.topDirPath+"/SPECS/"
        chrootLogsFilePath=chrootID+constants.topDirPath+"/LOGS/"+package+".log"
        chrootCmd=self.runInChrootCommand+" "+chrootID
        shutil.copyfile(specFile, chrootID+chrootSpecPath+specName )
        
        self.copySourcesTobuildroot(listSourcesFiles,package,chrootSourcePath)
        self.copySourcesTobuildroot(listPatchFiles,package,chrootSourcePath)
        
        listRPMFiles=[]
        try:
            listRPMFiles = self.buildRPM(chrootSpecPath+"/"+specName,chrootLogsFilePath, chrootCmd)
        except Exception as e:
            self.logger.error("Failed while building rpm:"+package)
            raise e
        finally:
            if destLogPath is not None:
                shutil.copy2(chrootLogsFilePath, destLogPath)

        for rpmFile in listRPMFiles:
            self.copyRPM(chrootID+"/"+rpmFile, constants.rpmPath)

    def buildRPM(self,specFile,logFile,chrootCmd):
        
        rpmBuildcmd= self.rpmbuildBinary+" "+self.rpmbuildBuildallOption+" "+self.rpmbuildNocheckOption
        rpmBuildcmd+=" "+specFile
        
        cmdUtils = CommandUtils()
        returnVal = cmdUtils.runCommandInShell(rpmBuildcmd, logFile, chrootCmd)
        if not returnVal:
            self.logger.error("Building rpm is failed "+specFile)
            raise Exception("RPM Build failed")
        
        #Extracting rpms created from log file
        logfile=open(logFile,'r')
        fileContents=logfile.readlines()
        logfile.close()
        listRPMFiles=[]
        for i in range(0,len(fileContents)):
            if re.search("^Wrote:",fileContents[i]):
                listcontents=fileContents[i].split()
                if (len(listcontents) == 2) and listcontents[1].strip()[-4:] == ".rpm" and listcontents[1].find("/RPMS/") != -1:
                    listRPMFiles.append(listcontents[1])
        
        return listRPMFiles    
    
    def findRPMFileForGivenPackage(self,package):
        cmdUtils = CommandUtils()
        version = constants.specData.getVersion(package)
        release = constants.specData.getRelease(package)
        listFoundRPMFiles = cmdUtils.findFile(package+"-"+version+"-"+release+"*.rpm",constants.rpmPath)
        if len(listFoundRPMFiles) == 1 :
            return listFoundRPMFiles[0]
        if len(listFoundRPMFiles) == 0 :
            return None
        if len(listFoundRPMFiles) > 1 :
            self.logger.error("Found multiple rpm files for given package in rpm directory.Unable to determine the rpm file for package:"+package)
            raise Exception("Multiple rpm files found")
    
    def findPackageNameFromRPMFile(self,rpmfile):
        rpmfile=os.path.basename(rpmfile)
        releaseindex=rpmfile.rfind("-")
        if releaseindex == -1:
            self.logger.error("Invalid rpm file:"+rpmfile)
            raise Exception("Invalid RPM")
        versionindex=rpmfile[0:releaseindex].rfind("-")
        if versionindex == -1:
            self.logger.error("Invalid rpm file:"+rpmfile)
            raise Exception("Invalid RPM")
        packageName=rpmfile[0:versionindex]
        return packageName 
    
    def findInstalledRPMPackages(self, chrootID):
        cmd = self.rpmBinary+" "+self.queryRpmPackageOptions
        chrootCmd=self.runInChrootCommand+" "+chrootID
        cmdUtils=CommandUtils()
        result=cmdUtils.runCommandInShell2(cmd, chrootCmd)
        return result
