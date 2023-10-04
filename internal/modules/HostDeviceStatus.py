import psutil
import subprocess

class HostDeviceStatus:

    def getCPUTemperature(self) -> str:
        try:
            temperature = psutil.sensors_temperatures()
            cpu_temperature = temperature['coretemp'][0].current  # Gantilah 'coretemp' dengan sensor yang sesuai pada sistem Anda
            return f"CPU Temperature: {cpu_temperature}°C"
        except Exception as e:
            return f"Failed to read CPU temperature: {e}"
    
    def getCPUUsage(self) -> str:
        cpu_percent = psutil.cpu_percent(interval=1)
        return f"CPU Usage: {cpu_percent}%"
    
    def getMemoryUsage(self) -> str:
        memory = psutil.virtual_memory()
        return f"Memory Usage: {memory.used / (1024 ** 3):.2f} GB"
    
    def getMemoryFree(self) -> str:
        memory = psutil.virtual_memory()
        return f"Available Memory: {memory.available / (1024 ** 3):.2f} GB"
    
    def getMemoryTotal(self) -> str:
        memory = psutil.virtual_memory()
        return f"Total Memory: {memory.total / (1024 ** 3):.2f} GB"

    def getStorageInfo(self) -> str:
        disk_partitions = psutil.disk_partitions()
        usage = psutil.disk_usage(disk_partitions[0].mountpoint)
        return f"Partition: {disk_partitions[0].device}" +\
        f"Total Space: {usage.total / (1024 ** 3):.2f} GB" +\
        f"Used Space: {usage.used / (1024 ** 3):.2f} GB" +\
        f"Free Space: {usage.free / (1024 ** 3):.2f} GB" +\
        f"Disk Usage: {usage.percent}%"
        
    def getUpTime(self) -> str:
        uptime = psutil.boot_time()
        return f"System Uptime: {uptime} seconds"
    
    def getFanSpeed(self) -> str:
        output = subprocess.check_output(["sensors"]).decode("utf-8")
        fan_speed_lines = [line for line in output.split('\n') if 'fan' in line.lower()]
        return fan_speed_lines[0]
    
    def brief(self):
        return {
            "cpu_temp": self.getCPUTemperature(),
            "cpu_usage": self.getCPUUsage(),
            "memory_usage": self.getMemoryUsage(),
            "memory_free": self.getMemoryFree(),
            "memory_total": self.getMemoryTotal(),
            "storage": self.getStorageInfo(),
            "up_time": self.getUpTime(),
            "fan_speed": self.getFanSpeed()
        }