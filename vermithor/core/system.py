import os
import platform


class SystemManager:

    def get_system_info(self):

        return (
            f"Operating system: {platform.system()} "
            f"{platform.release()}\n"
            f"Machine: {platform.machine()}\n"
            f"Processor: {platform.processor()}"
        )


    def get_current_directory(self):

        return os.getcwd()