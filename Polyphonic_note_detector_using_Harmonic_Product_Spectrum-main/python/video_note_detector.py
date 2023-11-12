# Project name: Polyphonic note detector using Harmonic Product Spectrum
# Date:         2021.05.19
# Author:       João Nuno Carvalho
# Description:  This is my implementation of a polyphonic note detector using
#               the Harmonic Product Spectrum method.
#               The input is a mono WAV file.
#               The output are the corresponding notes in time. 
# License: MIT Open Source License


import numpy as np
import matplotlib.pyplot as plt
import wave
import math
from scipy.signal import find_peaks
from moviepy.editor import *
import sys

## Configuration

# Path
# Expected terminal to be in tabs-generator folder
path     = "../data/"
exp_path = "./Polyphonic_note_detector_using_Harmonic_Product_Spectrum-main/labeled/"

# filename = '18461__pitx__a4.wav'
filename = filename = "dumb_scale_youtube.mp4"
# filename = '18474__pitx__c4.wav'
# filename = 'c_major_guitar.wav'
# filename = 'c_major_classical_guitar_E2_C3_E3_G3_C4_E4.wav'

# note_threshold = 5_000.0    # 120   # 50_000.0   #  3_000.0
THRESH = 100

# Parameters
sample_rate  = 44100                     # Sampling Frequency
# fft_len      = 22050                     # Length of the FFT window
fft_len      = 2048*4                      # Length of the FFT window
overlap      = 0.5                       # Hop overlap percentage between windows
hop_length   = int(fft_len*(1-overlap))  # Number of samples between successive frames

# For the calculations of the music scale.
TWELVE_ROOT_OF_2 = math.pow(2, 1.0 / 12)

def read_wav_file(path, filename):
    # Reads the input WAV file from HDD disc.
    wav_handler = wave.open(path + filename,'rb') # Read only.
    num_frames = wav_handler.getnframes()
    sample_rate = wav_handler.getframerate()
    wav_frames = wav_handler.readframes(num_frames)

    # Loads the file into a NumPy contiguous array.

    # Convert Int16 into float64 in the range of [-1, 1].
    # This means that the sound pressure values are mapped to integer values that can range from -2^15 to (2^15)-1.
    # We can convert our sound array to floating point values ranging from -1 to 1 as follows.
    signal_temp = np.frombuffer(wav_frames, np.int16)
    signal_array = np.zeros( len(signal_temp), float)

    for i in range(0, len(signal_temp)):
        signal_array[i] = signal_temp[i] / (2.0**15)

    # print("file_name: " + str(filename))
    # print("sample_rate: " + str(sample_rate))
    # print("input_buffer.size: " + str(len(signal_array)))
    # print("seconds: " + to_str_f4(len(signal_array)/sample_rate) + " s")
    # print("type [-1, 1]: " + str(signal_array.dtype))
    # print("min: " + to_str_f4(np.min(signal_array)) + " max: " + to_str_f4(np.max(signal_array))  )

    return sample_rate, signal_array

def read_video_file(path, filename):
    video = VideoFileClip(path + filename)
    fps = video.fps
    frame_filenames = video.write_images_sequence(path + "frame%04d.jpeg")
    audio = video.audio
    sample_rate = audio.fps
    signal_temp = np.array([n[0] for n in audio.iter_frames()])
    signal_array = np.zeros(len(signal_temp), float)
    for i in range(0, len(signal_temp)):
        signal_array[i] = signal_temp[i] / (2.0**15)
        
    return sample_rate, signal_array, frame_filenames


def divide_buffer_into_non_overlapping_chunks(buffer, max_len):
    buffer_len = len(buffer)
    chunks = int(buffer_len / max_len)
    print("buffers_num: " + str(chunks))
    division_pts_list = []
    for i in range(1, chunks):
        division_pts_list.append(i * max_len)    
    splitted_array_view = np.split(buffer, division_pts_list, axis=0)
    return splitted_array_view

def getFFT(data, rate):
    # Returns fft_freq and fft, fft_res_len.
    len_data = len(data)
    data = data * np.hamming(len_data)
    fft = np.fft.rfft(data)
    fft = np.abs(fft)
    ret_len_FFT = len(fft)
    freq = np.fft.rfftfreq(len_data, 1.0 / sample_rate)
    # return ( freq[:int(len(freq) / 2)], fft[:int(ret_len_FFT / 2)], ret_len_FFT )
    return ( freq, fft, ret_len_FFT )

def remove_dc_offset(fft_res):
    # Removes the DC offset from the FFT (First bin's)
    fft_res[0] = 0.0
    fft_res[1] = 0.0
    fft_res[2] = 0.0
    return fft_res

def freq_for_note(base_note, note_index):
    # See Physics of Music - Notes
    #     https://pages.mtu.edu/~suits/NoteFreqCalcs.html
    
    A4 = 440.0

    base_notes_freq = {"A2" : A4 / 4,   # 110.0 Hz
                       "A3" : A4 / 2,   # 220.0 Hz
                       "A4" : A4,       # 440.0 Hz
                       "A5" : A4 * 2,   # 880.0 Hz
                       "A6" : A4 * 4 }  # 1760.0 Hz  

    scale_notes = { "C"  : -9.0,
                    "C#" : -8.0,
                    "D"  : -7.0,
                    "D#" : -6.0,
                    "E"  : -5.0,
                    "F"  : -4.0,
                    "F#" : -3.0,
                    "G"  : -2.0,
                    "G#" : -1.0,
                    "A"  :  1.0,
                    "A#" :  2.0,
                    "B"  :  3.0,
                    "Cn" :  4.0}

    scale_notes_index = list(range(-9, 5)) # Has one more note.
    note_index_value = scale_notes_index[note_index]
    freq_0 = base_notes_freq[base_note]
    freq = freq_0 * math.pow(TWELVE_ROOT_OF_2, note_index_value) 
    return freq

def get_all_notes_freq():
    ordered_note_freq = []
    ordered_notes = ["C",
                     "C#",
                     "D",
                     "D#",
                     "E",
                     "F",
                     "F#",
                     "G",
                     "G#",
                     "A",
                     "A#",
                     "B"]
    for octave_index in range(2, 7):
        base_note  = "A" + str(octave_index)
        # note_index = 0  # C2
        # note_index = 12  # C3
        for note_index in range(0, 12):
            note_freq = freq_for_note(base_note, note_index)
            note_name = ordered_notes[note_index] + "_" + str(octave_index)
            ordered_note_freq.append((note_name, note_freq))
    return ordered_note_freq

def find_nearest_note(ordered_note_freq, freq):
    final_note_name = 'note_not_found'
    last_dist = 1_000_000.0
    for note_name, note_freq in ordered_note_freq:
        curr_dist = abs(note_freq - freq)
        if curr_dist < last_dist:
            last_dist = curr_dist
            final_note_name = note_name
        elif curr_dist > last_dist:
            break    
    return final_note_name

def PitchSpectralHps(X, freq_buckets, f_s, buffer_rms):

    """
    NOTE: This function is from the book Audio Content Analysis repository
    https://www.audiocontentanalysis.org/code/pitch-tracking/hps-2/
    The license is MIT Open Source License.
    And I have modified it. Go to the link to see the original.

    computes the maximum of the Harmonic Product Spectrum

    Args:
        X: spectrogram (dimension FFTLength X Observations)
        f_s: sample rate of audio data

    Returns:
        f HPS maximum location (in Hz)
    """

    # initialize
    iOrder = 4
    f_min = 65.41   # C2      300
    f = np.zeros(len(X))

    iLen = int((X.shape[0] - 1) / iOrder)
    afHps = X[np.arange(0, iLen)]
    k_min = int(round(f_min / f_s * 2 * (X.shape[0] - 1)))

    # compute the HPS
    for j in range(1, iOrder):
        X_d = X[::(j + 1)]
        afHps *= X_d[np.arange(0, iLen)]

    ## Uncomment to show the original algorithm for a single frequency or note. 
    # f = np.argmax(afHps[np.arange(k_min, afHps.shape[0])], axis=0)
    ## find max index and convert to Hz
    # freq_out = (f + k_min) / (X.shape[0] - 1) * f_s / 2
    afHps = np.clip(afHps, 0, max(afHps) * 0.5)

    note_threshold = note_threshold_scaled_by_RMS(buffer_rms)

    all_freq = np.argwhere(afHps[np.arange(k_min, afHps.shape[0])] > note_threshold)
    if max(afHps[np.arange(k_min, afHps.shape[0])] > buffer_rms * 2):
        max_index_peaks, find_peaks_dict = find_peaks(afHps[np.arange(k_min, afHps.shape[0])], height=max(afHps[np.arange(k_min, afHps.shape[0])]) / 10, distance=5)
    else:
        max_index_peaks, find_peaks_dict = find_peaks(afHps[np.arange(k_min, afHps.shape[0])], height=1, distance=8)
    # find max index and convert to Hz
    freqs_out = (max_index_peaks + k_min) / (X.shape[0] - 1) * f_s / 2
    # freqs_out = (all_freq + k_min) / (X.shape[0] - 1) * f_s / 2

    
    x = afHps[np.arange(k_min, afHps.shape[0])]
    freq_indexes_out = np.where( x > note_threshold)
    freq_values_out = x[max_index_peaks]
    # freq_values_out = x[freq_indexes_out]

    # print("\n##### x: " + str(x))
    # print("\n##### freq_values_out: " + str(freq_values_out))

    max_value = np.max(afHps[np.arange(k_min, afHps.shape[0])])
    max_index = np.argmax(afHps[np.arange(k_min, afHps.shape[0])])

    # fig, ax = plt.subplots()
    # ax.plot(afHps[np.arange(k_min, afHps.shape[0])])
    # plt.show()
    
    ## Uncomment to print the values: buffer_RMS, max_value, min_value
    ## and note_threshold.    
    # print(" buffer_rms: " + to_str_f4(buffer_rms) )
    # print(" max_value : " + to_str_f(max_value) + "  max_index : " + to_str_f(max_index) )
    # print(" note_threshold : " + to_str_f(note_threshold) )
    # print(" scipy peaks: " + str(max_index_peaks))

    ## Uncomment to show the graph of the result of the 
    ## Harmonic Product Spectrum. 
    # fig, ax = plt.subplots()
    # yr_tmp = afHps[np.arange(k_min, afHps.shape[0])]
    # xr_tmp = (np.arange(k_min, afHps.shape[0]) + k_min) / (X.shape[0] - 1) * f_s / 2
    # ax.plot(xr_tmp, yr_tmp)
    # plt.show()

    # Turns 2 level list into a one level list.
    freqs_out_tmp = []
    for freq, value  in zip(freqs_out, freq_values_out):
        freqs_out_tmp.append((freq, value))
    
    return freqs_out_tmp

def note_threshold_scaled_by_RMS(buffer_rms):
    note_threshold = THRESH * (4 / 0.090) * buffer_rms
    return note_threshold

def normalize(arr):
    # Note: Do not use.
    # Normalize array between -1 and 1.
    # Only works if the signal is larger then the final signal and if the positive
    # value is grater in absolute value them the negative value.
    ar_res = (arr / (np.max(arr) / 2)) - 1  
    return ar_res

def to_str_f(value):
    # Returns a string with a float without decimals.
    return "{0:.0f}".format(value)

def to_str_f4(value):
    # Returns a string with a float without decimals.
    return "{0:.4f}".format(value)


def main():
    print("\nPolyphonic note detector\n")
    
    ordered_note_freq = get_all_notes_freq()
    # print(ordered_note_freq)

    # sample_rate_file, input_buffer = read_wav_file(path, filename)
    sample_rate_file, input_buffer, frame_filenames = read_video_file(path, filename)
    buffer_chunks = divide_buffer_into_non_overlapping_chunks(input_buffer, fft_len)
    # The buffer chunk at n seconds:

    count = 0
    
    ## Uncomment to process a single chunk os a limited number os sequential chunks. 
    # for chunk in buffer_chunks[5: 6]:
    num_chunks = len(buffer_chunks)
    notes_per_chunk = [[]] * num_chunks
    note_names = []
    times = []
    for idx, chunk in enumerate(buffer_chunks):
        # print("\n...Chunk: ", str(count))
                
        fft_freq, fft_res, fft_res_len = getFFT(chunk, len(chunk))
        fft_res = remove_dc_offset(fft_res)

        # Calculate Root Mean Square of the signal buffer, as a scale factor to the threshold.
        buffer_rms = np.sqrt(np.mean(chunk**2))

        all_freqs = PitchSpectralHps(fft_res, fft_freq, sample_rate_file, buffer_rms)
        # print("Number of frequencies: " + str(len(all_freqs)))
        # print("all_freqs ")
        # print(all_freqs)

        time = float(fft_len) * idx / sample_rate_file

        for freq in all_freqs:
            note_name = find_nearest_note(ordered_note_freq, freq[0])
            note_names.append(note_name)
            notes_per_chunk[idx] = note_name
            times.append(time)
            # print("=> freq: " + to_str_f(freq[0]) + " Hz  value: " + to_str_f(freq[1]) + " note_name: " + note_name )

        ## Uncomment to print the arrays.
        # print("\nfft_freq: ")
        # print(fft_freq)
        # print("\nfft_freq_len: " + str(len(fft_freq)))

        # print("\nfft_res: ")
        # print(fft_res)

        # print("\nfft_res_len: ")
        # print(fft_res_len)


        # Uncomment to show the graph of the result of the FFT with the
        # correct frequencies in the legend. 
        # N = fft_res_len
        # fft_freq_interval = fft_freq[: N // 4]
        # fft_res_interval = fft_res[: N // 4]
        # fig, ax = plt.subplots()
        # ax.plot(fft_freq_interval, 2.0/N * np.abs(fft_res_interval))
        # plt.show()

        count += 1

    time_notes = np.array([times, note_names]).T
    frames_arr = np.array(frame_filenames).reshape((len(frame_filenames), 1))
    export_arr = np.zeros_like((len(frame_filenames), 2), dtype=str)
    frames_per_chunk = len(frame_filenames) / count

    for idx, fn in enumerate(frame_filenames):

        export_arr[idx,:] = [fn, note_names[int(idx / frames_per_chunk)]]
    np.savetxt(exp_path + filename.split(".")[0] + "-labeled.csv", export_arr, fmt="%s")


    # print("export to csv:")
    # print(export_arr)

if __name__ == "__main__":
    main()








