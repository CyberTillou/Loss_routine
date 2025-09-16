import os
import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt

# === Base path to measurement folders ===
base_folder = r"C:\Users\tperson\Desktop\loss_measurment\measurment_result\guide-76"

# === Locate TE, TM, and RAW subfolders ===
te_folder = ""
tm_folder = ""
raw_folder = ""

for folder in os.listdir(base_folder):
    if folder.endswith("losses_TE"):
        te_folder = os.path.join(base_folder, folder)
    elif folder.endswith("losses_TM"):
        tm_folder = os.path.join(base_folder, folder)
    elif folder.endswith("losses_raw"):
        raw_folder = os.path.join(base_folder, folder)

if not all([te_folder, tm_folder, raw_folder]):
    print("[ERROR] One or more folders are missing (TE, TM, raw)")
    exit()

# === Read data from text files ===
def read_data(filepath):
    wavelengths = []
    powers = []
    with open(filepath, "r") as f:
        next(f)  # skip header
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    wl = float(parts[0])
                    p = float(parts[1])
                    wavelengths.append(wl)
                    powers.append(p)
                except:
                    continue
    return np.array(wavelengths), np.array(powers)

# Load data
wl_te, power_te = read_data(os.path.join(te_folder, "data.txt"))
wl_tm, power_tm = read_data(os.path.join(tm_folder, "data.txt"))
wl_raw, power_raw = read_data(os.path.join(raw_folder, "data.txt"))

# Check wavelength consistency
if not (np.allclose(wl_te, wl_raw) and np.allclose(wl_tm, wl_raw)):
    print("[ERROR] Wavelength mismatch between files.")
    exit()

# === Normalize TE and TM power by RAW ===
ratio_te = np.divide(power_te, power_raw, out=np.zeros_like(power_te), where=power_raw != 0)
ratio_tm = np.divide(power_tm, power_raw, out=np.zeros_like(power_tm), where=power_raw != 0)

# === Fabry-Perot loss calculation ===
def find_peaks(wl, power, peak_dist_nm=0.1):
    step = wl[1] - wl[0]
    distance_pts = peak_dist_nm / step
    ind_max = signal.find_peaks(power, distance=distance_pts)[0]
    ind_min = signal.find_peaks(-power, distance=distance_pts)[0]
    return ind_max, ind_min

def get_mode_parameters(mode="TM"):
    mode = mode.upper()
    if mode == "TE":
        R = 0.2956
        n_eff = 3.087435
    elif mode == "TM":
        R = 0.2287
        n_eff = 3.073054
    else:
        raise ValueError("Invalid mode. Use 'TE' or 'TM'.")
    return R, n_eff

def calculate_loss(wl, power, ind_max, ind_min, R, n_eff):
    loc_max = wl[ind_max]
    loc_min = wl[ind_min]

    mean_max = np.mean(power[ind_max])
    mean_min = np.mean(power[ind_min])

    K = (mean_max - mean_min) / (mean_max + mean_min)
    R_tilde = (1 - np.sqrt(1 - K**2)) / K

    fsr_lambda = loc_max[5] - loc_max[4]
    L_meas = (loc_max[0]**2) / (2 * n_eff * (loc_max[1] - loc_max[0])) * 1e-9

    loss_cm = np.log(R / R_tilde) / L_meas / 1e2
    return loss_cm

# === Compute losses on normalized data ===
R_te, n_eff_te = get_mode_parameters("TE")
indmax_te, indmin_te = find_peaks(wl_te, ratio_te)
loss_te = calculate_loss(wl_te, ratio_te, indmax_te, indmin_te, R_te, n_eff_te)
print(f"[TE] Optical loss: {loss_te:.3f} cm⁻¹")

R_tm, n_eff_tm = get_mode_parameters("TM")
indmax_tm, indmin_tm = find_peaks(wl_tm, ratio_tm)
loss_tm = calculate_loss(wl_tm, ratio_tm, indmax_tm, indmin_tm, R_tm, n_eff_tm)
print(f"[TM] Optical loss: {loss_tm:.3f} cm⁻¹")

# === Plot everything on one figure ===
plt.figure(figsize=(10, 6))
plt.plot(wl_te, ratio_te, label=f"TE/raw — loss = {loss_te:.3f} cm⁻¹", color="blue")
plt.plot(wl_tm, ratio_tm, label=f"TM/raw — loss = {loss_tm:.3f} cm⁻¹", color="green")
plt.xlabel("Wavelength (nm)")
plt.ylabel("Normalized Power (a.u.)")
plt.title("Normalized Fabry-Perot Spectrum and Optical Loss")
plt.grid(True, linestyle=":")
plt.legend()
plt.tight_layout()
plt.show()
