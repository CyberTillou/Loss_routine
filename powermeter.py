import ctypes
import time
import sys

# Structure used to represent the measurement data received from the device.
class DataPacketType(ctypes.Structure):
    _fields_ = [("measure", ctypes.c_float), ("period", ctypes.c_int)]


# This class loads the DLL and configures function signatures for proper ctypes usage.
class FM_DLL:
    def __init__(self, dll_path):
        """
        dll_path: str - Full path to the DLL file
        """
        self.dll = ctypes.CDLL(dll_path)
        self._configure_functions()

    def _configure_functions(self):
        """
        Configure the argument and return types for all the DLL functions used.
        """
        # Initialization and deinitialization
        self.dll.fm2LibInit.restype = ctypes.c_int
        self.dll.fm2LibDeInit.restype = None

        # Open and close driver
        self.dll.fm2LibOpenDriver.argtypes = [ctypes.c_int]
        self.dll.fm2LibOpenDriver.restype = ctypes.c_int
        self.dll.fm2LibCloseDriver.argtypes = [ctypes.c_int]

        # Sync communication
        self.dll.fm2LibSync.argtypes = [ctypes.c_int]
        self.dll.fm2LibSync.restype = ctypes.c_bool

        # Get serial number
        self.dll.fm2LibGetSerialNumber.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
        self.dll.fm2LibGetSerialNumber.restype = ctypes.c_bool

        # Get data
        self.dll.fm2LibGetData.argtypes = [
            ctypes.c_int,
            ctypes.POINTER(DataPacketType),
            ctypes.POINTER(ctypes.c_int)
        ]
        self.dll.fm2LibGetData.restype = ctypes.c_bool


# This class handles initialization and communication with the device.
class FM_Communication:
    def __init__(self, dll_wrapper, device_index=0):
        """
        dll_wrapper: FM_DLL - Instance of the FM_DLL class
        device_index: int - Index of the device (default: 0)
        """
        self.dll = dll_wrapper.dll
        self.device_index = device_index
        self.handle = None

    def initialize(self):
        """
        Initializes the FieldMax DLL.
        """
        if self.dll.fm2LibInit() != 0:
            print("Driver successfully initialized.")
        else:
            raise RuntimeError("Failed to initialize the DLL.")

    def open(self):
        """
        Opens the driver and gets the device handle.
        """
        self.handle = self.dll.fm2LibOpenDriver(self.device_index)
        if self.handle == -1:
            raise RuntimeError(f"Failed to open the device. System error: {ctypes.get_last_error()}")
        print(f"Device opened successfully with handle: {self.handle}")

    def close(self):
        """
        Closes the device driver.
        """
        if self.handle is not None:
            self.dll.fm2LibCloseDriver(self.device_index)

    def deinitialize(self):
        """
        Deinitializes the FieldMax DLL.
        """
        self.dll.fm2LibDeInit()


# This class performs device communication synchronization.
class FM_Synchronizer:
    def __init__(self, dll_wrapper, handle):
        """
        dll_wrapper: FM_DLL - Instance of the FM_DLL class
        handle: int - Handle to the opened device
        """
        self.dll = dll_wrapper.dll
        self.handle = handle

    def synchronize(self):
        """
        Resynchronizes communication with the FieldMax device.
        """
        if self.dll.fm2LibSync(self.handle):
            print("Communication successfully resynchronized.")
        else:
            raise RuntimeError(f"Failed to resynchronize communication. System error: {ctypes.get_last_error()}")


# This class retrieves device information like the serial number.
class FM_DeviceInfo:
    def __init__(self, dll_wrapper, handle):
        """
        dll_wrapper: FM_DLL - Instance of the FM_DLL class
        handle: int - Handle to the opened device
        """
        self.dll = dll_wrapper.dll
        self.handle = handle

    def get_serial_number(self):
        """
        Returns the serial number of the device.
        return: str
        """
        serial_size = ctypes.c_int(1024)
        serial_buffer = ctypes.create_string_buffer(256)
        success = self.dll.fm2LibGetSerialNumber(
            self.handle, serial_buffer, ctypes.byref(serial_size)
        )
        if not success:
            raise RuntimeError("Failed to retrieve the serial number.")
        return serial_buffer.value.decode('utf-8')


# This class handles acquisition of power/energy measurements from the device.
class FM_Measure:
    def __init__(self, dll_wrapper, handle, max_count=8):
        """
        dll_wrapper: FM_DLL - Instance of the FM_DLL class
        handle: int - Handle to the opened device
        max_count: int - Max number of measurements to retrieve
        """
        self.dll = dll_wrapper.dll
        self.handle = handle
        self.max_count = max_count
        self.data_buffer = (DataPacketType * max_count)()

    def get_measurements(self, iterations=5, delay=1):
        for i in range(iterations):
            count = ctypes.c_int(self.max_count)
            result = self.dll.fm2LibGetData(self.handle, self.data_buffer, ctypes.byref(count))
            #print(f"Essai {i+1} - Résultat: {result}, Nombre mesures: {count.value}")
            #if not result:
            #    print("Erreur lors de la lecture des données.")
            #elif count.value == 0:
            #    print("Aucune donnée mesurée.")
            #else:
            #    print(f"Mesure 0: {self.data_buffer[0].measure}")
            time.sleep(delay)
        return self.data_buffer[0].measure


