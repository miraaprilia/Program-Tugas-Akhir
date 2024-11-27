import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import serial
import serial.tools.list_ports
import threading

# Create the main window
root = tk.Tk()
root.title("Exoskeleton PID Control GUI")
root.geometry("1500x850")

# Initialize serial connection variable
serial_connection = None
data_buffer = []  # Buffer to store data received from serial port

# Scan available serial ports
def scan_ports():
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

# Update serial port options
def update_ports():
    ports = scan_ports()
    serial_port['values'] = ports
    if ports:
        serial_port.set(ports[0])  # Set to the first available port

# Connect to Arduino
def connect_to_arduino():
    global serial_connection
    selected_port = serial_port.get()
    if selected_port:
        try:
            serial_connection = serial.Serial(selected_port, 9600, timeout=1)
            print(f"Connected to {selected_port}")
            led_canvas.itemconfig(led_circle, fill="green")  # Turn on LED
            threading.Thread(target=read_serial_data, daemon=True).start()
            label_serial_status.config(text=f"Connected to {selected_port}")  # Update connection status
        except serial.SerialException as e:
            print(f"Failed to connect to {selected_port}: {e}")
            label_serial_status.config(text="Connection Failed")  # Update connection status

# Disconnect from Arduino
def disconnect_from_arduino():
    global serial_connection
    if serial_connection and serial_connection.is_open:
        serial_connection.close()
        print("Disconnected")
        led_canvas.itemconfig(led_circle, fill="red")  # Turn off LED
        label_serial_status.config(text="Not Connected")  # Update connection status

# Read data from Arduino
def read_serial_data():
    global serial_connection, data_buffer
    while serial_connection and serial_connection.is_open:
        try:
            line = serial_connection.readline().decode('utf-8').strip()
            if line:
                print(f"Diterima: {line}")  # Debug print
                # Split data menjadi parameter RPM dan arah
                if "RPM:" in line and "Arah:" in line:
                    parts = line.split(', ')
                    for part in parts:
                        key, value = part.split(':')
                        if key.strip() == "RPM":
                            label_rpm_value.config(text=value.strip())
                            data_buffer.append(float(value.strip()))
                            if len(data_buffer) > 1000:
                                data_buffer.pop(0)
                        elif key.strip() == "Arah":
                            label_direction_value.config(text=value.strip())

                    # Update plot
                    plot_response()

        except serial.SerialException as e:
            print(f"Kesalahan serial: {e}")
            break

# Plot step response
def plot_response():
    ax.clear()  # Clear previous plot

    if not data_buffer:
        return

    # Update plot with real-time data
    t = np.arange(len(data_buffer)) * 0.1
    y = np.array(data_buffer)

    final_value = y[-1]
    t_rise_start = t[np.where(y >= 0.1 * final_value)[0][0]] if any(y >= 0.1 * final_value) else 0
    t_rise_end = t[np.where(y >= 0.9 * final_value)[0][0]] if any(y >= 0.9 * final_value) else 0
    rise_time = round(t_rise_end - t_rise_start, 4) if t_rise_end > t_rise_start else 0

    peak_index = np.argmax(y)
    peak_time = round(t[peak_index], 4)
    peak_value = round(y[peak_index], 4)
    overshoot = round((y[peak_index] - final_value) / final_value * 100, 2) if final_value != 0 else 0

    settling_threshold = 0.02 * final_value
    settling_time = round(t[np.where(np.abs(y - final_value) <= settling_threshold)[0][-1]],
                          4) if any(np.abs(y - final_value) <= settling_threshold) else 0

    ax.plot(t, y, label="Real-time Response", color="blue")
    ax.axvline(x=t_rise_start, color='red', linestyle='--', label='Rise Start')
    ax.axvline(x=t_rise_end, color='green', linestyle='--', label='Rise End')
    ax.axvline(x=peak_time, color='magenta', linestyle='--', label='Peak Time')
    ax.axvline(x=settling_time, color='yellow', linestyle='--', label='Settling Time')
    ax.axhline(y=peak_value, color='cyan', linestyle='--', label='Peak Value')

    ax.set_title("Real-time Step Response with Transient Characteristics")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
    ax.legend()
    ax.grid()

    canvas.draw()

    # Update transient response information
    label_rise_time.config(text=f"Rise Time: {rise_time} s")
    label_settling_time.config(text=f"Settling Time: {settling_time} s")
    label_overshoot.config(text=f"Overshoot: {overshoot} %")
    label_peak.config(text=f"Peak: {peak_value}")

    # Update real-time motor data
    label_rpm_value.config(text=f"{data_buffer[-1]:.0f}")
    label_direction_value.config(text=f"{direction_var.get()}")

# Function for controlling the motor
def control_motor():
    global serial_connection
    rpm = rpm_entry.get()
    direction = direction_var.get()

    # Validasi input RPM
    try:
        rpm_value = float(rpm)
        if rpm_value < 0:
            raise ValueError("RPM tidak boleh negatif")
    except ValueError as e:
        print(f"Input RPM tidak valid: {e}")
        label_rpm.config(text="RPM: Invalid")
        return

    # Buat perintah untuk Arduino
    rpm_command = f"SET RPM:{rpm_value}\n"
    direction_command = f"Arah:{direction}\n"

    if serial_connection and serial_connection.is_open:
        try:
            # Kirim perintah melalui Serial
            serial_connection.write(rpm_command.encode())
            serial_connection.write(direction_command.encode())
            print(f"Dikirim: {rpm_command.strip()}")
            print(f"Dikirim: {direction_command.strip()}")
        except serial.SerialException as e:
            print(f"Kesalahan komunikasi serial: {e}")
    else:
        print("Belum terhubung ke Arduino!")

# Frame for plot
frame_plot = tk.LabelFrame(root, text="Step Response Plot", padx=10, pady=10)
frame_plot.place(x=20, y=20, width=600, height=430)

fig, ax = plt.subplots(figsize=(5, 4), dpi=100)
canvas = FigureCanvasTkAgg(fig, master=frame_plot)
canvas.get_tk_widget().pack()

frame_pid = tk.LabelFrame(root, text="PID Tuning Parameters", padx=10, pady=10)
frame_pid.place(x=650, y=20, width=300, height=220)

# PID parameters input
tk.Label(frame_pid, text="Kp").grid(row=0, column=0, padx=5, pady=5)
kp_input = tk.Entry(frame_pid)
kp_input.insert(0, "2.0")
kp_input.grid(row=0, column=1, padx=5, pady=5)

tk.Label(frame_pid, text="Ki").grid(row=1, column=0, padx=5, pady=5)
ki_input = tk.Entry(frame_pid)
ki_input.insert(0, "0.5")
ki_input.grid(row=1, column=1, padx=5, pady=5)

tk.Label(frame_pid, text="Kd").grid(row=2, column=0, padx=5, pady=5)
kd_input = tk.Entry(frame_pid)
kd_input.insert(0, "0.1")
kd_input.grid(row=2, column=1, padx=5, pady=5)

button_plot = tk.Button(frame_pid, text="Plot Response", command=plot_response, width=20)
button_plot.grid(row=4, column=0, columnspan=2, pady=(10, 5))

# Frame for transient response info
frame_info = tk.LabelFrame(root, text="Transient Response Info", padx=10, pady=10)
frame_info.place(x=650, y=250, width=300, height=220)

label_rise_time = tk.Label(frame_info, text="Rise Time: -")
label_rise_time.grid(row=0, column=0, sticky="w")

label_settling_time = tk.Label(frame_info, text="Settling Time: -")
label_settling_time.grid(row=1, column=0, sticky="w")

label_overshoot = tk.Label(frame_info, text="Overshoot: -")
label_overshoot.grid(row=2, column=0, sticky="w")

label_peak = tk.Label(frame_info, text="Peak: -")
label_peak.grid(row=3, column=0, sticky="w")

# Real-time motor data
label_rpm_title = tk.Label(frame_info, text="Current RPM:")
label_rpm_title.grid(row=4, column=0, sticky="w")
label_rpm_value = tk.Label(frame_info, text="-")
label_rpm_value.grid(row=4, column=1, sticky="w")

label_direction_title = tk.Label(frame_info, text="Current Direction:")
label_direction_title.grid(row=5, column=0, sticky="w")
label_direction_value = tk.Label(frame_info, text="-")
label_direction_value.grid(row=5, column=1, sticky="w")

# Frame for motor control
frame_motor_control = tk.LabelFrame(root, text="Motor Control", padx=10, pady=10)
frame_motor_control.place(x=20, y=520, width=600, height=150)

# RPM Input
tk.Label(frame_motor_control, text="RPM").grid(row=0, column=0, padx=5, pady=5)
rpm_entry = tk.Entry(frame_motor_control)
rpm_entry.grid(row=0, column=1, padx=5, pady=5)
rpm_entry.insert(0, "1000")  # Default RPM value

# Direction Selection
tk.Label(frame_motor_control, text="Direction").grid(row=1, column=0, padx=5, pady=5)
direction_var = tk.StringVar(value="Clockwise")  # Default direction

# Radio buttons for direction
rb_clockwise = tk.Radiobutton(frame_motor_control, text="Clockwise", variable=direction_var, value="Clockwise")
rb_counterclockwise = tk.Radiobutton(frame_motor_control, text="Counterclockwise", variable=direction_var, value="Counterclockwise")
rb_clockwise.grid(row=1, column=1, padx=5, pady=5)
rb_counterclockwise.grid(row=1, column=2, padx=5, pady=5)

# Control Button
button_control = tk.Button(frame_motor_control, text="Set Motor", command=control_motor, width=20)
button_control.grid(row=2, column=0, columnspan=3, pady=(10, 5))

# Frame for LED indicator
led_frame = tk.Frame(root)
led_frame.place(x=20, y=680)
led_canvas = tk.Canvas(led_frame, width=20, height=20)
led_canvas.pack()
led_circle = led_canvas.create_oval(5, 5, 15, 15, fill="red")  # Red indicates disconnected

# Serial Port Selection
serial_port = ttk.Combobox(root)
serial_port.place(x=700, y=680, width=150)
update_ports()

# Connect and Disconnect Buttons
button_connect = tk.Button(root, text="Connect", command=connect_to_arduino)
button_connect.place(x=860, y=680)

button_disconnect = tk.Button(root, text="Disconnect", command=disconnect_from_arduino)
button_disconnect.place(x=960, y=680)

# Connection Status Label
label_serial_status = tk.Label(root, text="Not Connected")
label_serial_status.place(x=700, y=730)  # Adjust position as needed


# Start the GUI loop
root.mainloop()