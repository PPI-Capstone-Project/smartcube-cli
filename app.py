from internal.modules.VideoProcessor import VideoProcessor
from internal.modules.ModelRegistrar import ModelRegistrar
from internal.modules.DeviceRegistrar import DeviceRegistrar
from internal.modules.Notification import Notification
from internal.modules.HostDeviceStatus import HostDeviceStatus
from internal.modules.MQTT import MQTTService
from internal.modules.CommandManager import CommandManager
from internal.modules.Config import Config
from internal.modules.ModelManager import ModelManager
from internal.modules.HttpClient import HttpClient
from internal.contracts.IDevice import CameraDevice
from internal.contracts.IObjectDetectorModel import IObjectDetectorModel
from internal.contracts.IHttpClient import IHttpClient
import threading
import multiprocessing
import time
import json
from dotenv import dotenv_values, load_dotenv

if load_dotenv() == False:
    print(".env not found")

def instantiateDevice(device: dict[str, CameraDevice], videoProcessor: VideoProcessor, notificationService: Notification):
    model: IObjectDetectorModel = device["assigned_model_class"](videoProcessor)  # type: ignore
    device["device_instance"].streamVideoFrame(lambda frame: videoProcessor.presentInWindow(
        model.inferenceFrame(frame, 0.5, 0.6, 60, 50, notificationService.handleOnObjectDetected)))

def main():

    # Device process list
    processes: list[multiprocessing.Process] = []

    # Init pre configured http client
    httpClient = HttpClient()

    # Init Video Processor
    videoProcessor = VideoProcessor()

    # Init Registered Models
    modelRegistrar = ModelRegistrar()
    modelRegistrar.load()

    # Init Model Manager
    modelManager = ModelManager(modelRegistrar=modelRegistrar)

    # Init All Devices In config/devices.json
    deviceRegistar = DeviceRegistrar()
    deviceRegistar.loadCamera(modelRegistrar=modelRegistrar, videoProcessor=videoProcessor)

    # Init Notification Module
    notificationService = Notification(videoProcessor=videoProcessor, httpClient=httpClient)

    # Init Host Devices Status Module
    hostDevice = HostDeviceStatus()

    # Config
    config = Config()

    # Connect to MQTT
    mqttService = MQTTService()

    # Restart Device Process
    def restartDevice(processIndex, messageMetadata):
        processes[int(processIndex)].terminate()
        time.sleep(1)
        processes[int(processIndex)] = multiprocessing.Process(
            target=instantiateDevice,
            args=(deviceRegistar.getDevicesInstance()[int(processIndex)],
                  videoProcessor,
                  notificationService))
        processes[int(processIndex)].daemon = True
        processes[int(processIndex)].start()

    # Start Device Process
    def startDevice(processIndex, messageMetadata):
        # print(deviceRegistar.getDevicesInstance())
        p = multiprocessing.Process(
            target=instantiateDevice,
            args=(deviceRegistar.getDevicesInstance()[int(processIndex)],
                  videoProcessor,
                  notificationService))
        p.daemon = True
        p.start()

        processes.append(p)

    def syncEdgeConfig(arg, metadata):
        try:
            response = httpClient.getSession.get(f"{httpClient.baseUrl()}/edge-device-config")
            if response.status_code == 200:
                
                #Rewrite devices.json to sync configuration between backend to edge config
                devicesConfig = {"devices": json.loads(response.content.decode())["data"]}
                with open('internal/config/devices.json', "w") as outfile:
                    outfile.write(json.dumps(devicesConfig, indent=4))

                print("Edge config synchronized.")

                #Reload Device configuration
                deviceRegistar.reloadCamera(modelRegistrar=modelRegistrar, videoProcessor=videoProcessor)

            else:
                print(f"Failed to fetch edge devices config. Status code: {response.status_code}")

        except json.JSONDecodeError as e:
            print(f"Error synchronize edge config: {e}")

    # Prepare command manager
    def commandManager():
        # command response
        hostDeviceStatusData = json.dumps({'command': '/hostDeviceStatus', 'data': hostDevice.brief()}, indent=4)
        deviceConfigData = json.dumps({'command': '/getDeviceConfig', 'data': config.getDevicesConfig()}, indent=4)
        installedModelsData = json.dumps({'command': '/getInstalledModels', 'data': modelManager.getRegisteredModelsMetadata()}, indent=4)

        # Command Manager
        commandManager = CommandManager()
        commandManager.registerCommand("/restartDevice", '', restartDevice)
        commandManager.registerCommand("/startDevice", '', startDevice)
        commandManager.registerCommand("/getProcesses", '', lambda arg, metadata: mqttService.publish(processes.__str__()))
        commandManager.registerCommand("/hostDeviceStatus", '', lambda arg, metadata: mqttService.publish(hostDeviceStatusData))
        commandManager.registerCommand("/getDeviceConfig", '', lambda arg, metadata: mqttService.publish(deviceConfigData))
        commandManager.registerCommand("/getInstalledModels", '', lambda arg, metadata: mqttService.publish(installedModelsData))
        commandManager.registerCommand("/syncEdgeConfig", "", syncEdgeConfig)

        # Recieve message and process the command
        mqttService.run(commandManager.receiveMessage)

    # Listening to Remote Command using MQTT Protocol
    commandListener = threading.Thread(target=commandManager)
    commandListener.start()

    # Instantiate in multi process
    for device in deviceRegistar.getDevicesInstance():
        p = multiprocessing.Process(target=instantiateDevice, args=(
            device, videoProcessor, notificationService))
        p.daemon = True
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

if __name__ == '__main__':
    main()
