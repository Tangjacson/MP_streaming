import os


COOKED_TRACE_FOLDER = './cooked_traces/'
COOKED_RTT_FOLDER = './cooked_rtt/'

def load_trace(cooked_trace_folder=COOKED_TRACE_FOLDER):
    cooked_files = os.listdir(cooked_trace_folder)
    all_cooked_time = []
    all_cooked_bw = []
    all_file_names = []
    for cooked_file in cooked_files:
        file_path = cooked_trace_folder + cooked_file
        cooked_time = []
        cooked_bw = []
        # print file_path
        with open(file_path, 'rb') as f:
            for line in f:
                parse = line.split()
                cooked_time.append(float(parse[0]))
                cooked_bw.append([float(parse[1]), float(parse[3]), float(parse[5]), float(parse[7])])
        all_cooked_time.append(cooked_time)
        all_cooked_bw.append(cooked_bw)
        all_file_names.append(cooked_file)

    return all_cooked_time, all_cooked_bw, all_file_names

def load_rtt(cooked_trace_folder=COOKED_RTT_FOLDER):
    cooked_files = os.listdir(cooked_trace_folder)
    all_cooked_time = []
    all_cooked_rtt = []
    all_file_names = []
    for cooked_file in cooked_files:
        file_path = cooked_trace_folder + cooked_file
        cooked_time = []
        cooked_rtt = []
        # print file_path
        with open(file_path, 'rb') as f:
            for line in f:
                parse = line.split()
                cooked_time.append(float(parse[0]))
                cooked_rtt.append([float(parse[3]), float(parse[4]), float(parse[5]), float(parse[6])])
        all_cooked_time.append(cooked_time)
        all_cooked_rtt.append(cooked_rtt)
        all_file_names.append(cooked_file)

    return all_cooked_time, all_cooked_rtt, all_file_names