import sys
import time
import datetime
from scipy import signal
import numpy as np
from playsound import playsound
import threading
import oe_pyprocessor


def play_audio_thread():
    try:
        playsound(r'C:\\Users\\Utente\\Documents\\Open Ephys\\pink_noise_35dB_SPL_moreira.m4a', False)
    except Exception as e:
        print('Exception playing file:', e)


def butter_bandpass(low_cut, high_cut, sample_rate, order=2):
    return signal.butter(order, [low_cut, high_cut], btype='bandpass', output='sos', fs=sample_rate)


def butter_bandpass_filter(sos, data):
    return signal.sosfiltfilt(sos, data)


class PyProcessor:

    def __init__(self, processor, num_channels, sample_rate):
        self.eeg_threshold = 2.3
        self.emg_threshold = 10
        self.micro_volts_threshold = -90  # -90 micro volts.
        self.sos_delta = []
        self.sos_beta = []
        self.sos_emg = []
        sos_delta_f = butter_bandpass(0.5, 4, sample_rate)
        sos_beta_f = butter_bandpass(20, 30, sample_rate)
        sos_emg_f = butter_bandpass(10, 50, sample_rate)

        for i in range(num_channels):
            if i == 0:
                #  Ignores the first channel.
                continue
            self.sos_delta.append(sos_delta_f)
            self.sos_beta.append(sos_beta_f)
            self.sos_emg.append(sos_emg_f)

        self.sos_delta = np.asarray(self.sos_delta)
        self.sos_beta = np.asarray(self.sos_beta)
        self.sos_emg = np.asarray(self.sos_emg)

        self.buffer_eeg = []
        self.buffer_emg = []
        self.packet_count = 0
        self.packets_threshold = 256  # 4 seconds epoch.
        self.NREM = False

        current_time_str = (datetime.datetime.now()
                            .strftime("%Y%m%d_%H%M%S"))
        self.file_path = (f"C:\\Users\\Utente\\Desktop\\"
                          f"txt_peak_sw\\time_peaks_{current_time_str}.txt")
        self.file = None
        print('Initialization completed.')

    def process(self, data):
        try:
            self.buffer_eeg.append(data[1])
            self.buffer_emg.append(data[3])
            self.packet_count += 1

            if self.packet_count == self.packets_threshold:  # 4 seconds epoch.
                self.packet_count = 0

                data_delta = butter_bandpass_filter(self.sos_delta[0], np.concatenate(self.buffer_eeg))
                data_beta = butter_bandpass_filter(self.sos_beta[0], np.concatenate(self.buffer_eeg))
                data_emg = butter_bandpass_filter(self.sos_emg[2], np.concatenate(self.buffer_emg))

                rms_delta = np.sqrt(np.mean([x ** 2 for x in data_delta]))
                rms_beta = np.sqrt(np.mean([x ** 2 for x in data_beta]))
                rms_emg = np.sqrt(np.mean([x ** 2 for x in data_emg]))
                rms_ratio = rms_delta / rms_beta
                if rms_ratio > self.eeg_threshold and rms_emg < self.emg_threshold:
                    self.NREM = True
                else:
                    self.NREM = False
                self.buffer_eeg = []
                self.buffer_emg = []
                sys.exit()  # Exit the method.

            if self.NREM:
                signs = [1 if x < y else 0 if x == y else -1 for x, y in zip(data[1][:-1], data[1][1:])]

                for i in range(len(signs) - 1):
                    if signs[i] == -1. and signs[i + 1] == 1. and data[1][i] < self.micro_volts_threshold and data[1][i + 1] < self.micro_volts_threshold:
                        peak_time = time.perf_counter()
                        audio_thread = threading.Thread(target=play_audio_thread, args=())
                        audio_thread.start()
                        audio_thread.join()  # Waits for the audio to finish.
                        audio_end_time = time.perf_counter()
                        self.file.write(f"Peak {peak_time}\n")
                        self.file.write(f"Audio {audio_end_time}\n")
                        time.sleep(0.250)
                        break

        except Exception as e:
            print('Exception happened:', e)
            pass

    def start_acquisition(self):
        pass

    def stop_acquisition(self):
        pass

    def handle_ttl_event(self, source_node, channel, sample_number, line, state):
        pass

    def handle_spike(self, source_node, electrode_name, num_channels, num_samples, sample_number, sorted_id, spike_data):
        pass

    def start_recording(self, recording_dir):
        self.file = open(self.file_path, "a")  # Append at the end of line mode.
        self.file.write(f"Start {time.perf_counter()}\n")

    def stop_recording(self):
        self.file.close()
