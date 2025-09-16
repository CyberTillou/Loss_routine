import pyvisa

class TunicsLaser:
    def __init__(self, resource_address):
        self.rm = pyvisa.ResourceManager()
        try:
            self.inst = self.rm.open_resource(resource_address)
            self.inst.write_termination = '\r'
            self.inst.read_termination = '\r'
            self.inst.timeout = 5000  # Timeout in milliseconds
            print(f"Tunics Laser connected at {resource_address}")
        except Exception as e:
            raise ConnectionError(f"Could not connect to Tunics Laser: {e}")

    # ---------- Optical Output Control ----------
    def enable_output(self):
        """Enable optical output."""
        self.inst.write("ENABLE")

    def disable_output(self):
        """Disable optical output."""
        self.inst.write("DISABLE")

    # ---------- Output Power Settings ----------
    def set_power_dbm(self, power_dbm):
        """Set output power in dBm."""
        self.inst.write(f"DBM={power_dbm:.2f}")

    def set_power_mw(self, power_mw):
        """Set output power in mW."""
        self.inst.write(f"MW={power_mw:.2f}")

    def set_power_p(self, power):
        """Set output power using 'P=' command (unspecified unit)."""
        self.inst.write(f"P={power}")

    def get_power(self):
        """Query current output power."""
        return self.inst.query("P?")

    # ---------- Diode Current Settings ----------
    def set_current(self, current_value):
        """Set diode current."""
        self.inst.write(f"I={current_value}")

    def get_current(self):
        """Query current diode current."""
        return self.inst.query("I?")

    def get_current_limit(self):
        """Query current limit."""
        return self.inst.query("LIMIT?")

    # ---------- Wavelength / Frequency ----------
    def set_wavelength(self, wavelength_nm):
        """Set emission wavelength in nm."""
        self.inst.write(f"L={wavelength_nm:.3f}")

    def get_wavelength(self):
        """Query current emission wavelength."""
        return self.inst.query("L?")

    # ---------- Utility ----------
    def identify(self):
        """Return the laser's ID string."""
        return self.inst.query("*IDN?")

    def close(self):
        """Close the VISA resource."""
        self.inst.close()
        self.rm.close()

def main():
    resource_address = "ASRL4::INSTR"
    laser = None  # Initialisation

    try:
        # Création de l'instance du laser
        laser = TunicsLaser(resource_address)

        # Exemple de commande supportée par le laser
        print("Current wavelenght :", laser.get_wavelength())

    except Exception as e:
        print("Error of communication with laser :", e)

    finally:
        if laser is not None:
            laser.close()
            print("Communication with laser closed.")


if __name__ == "__main__":
    main()