import numpy as np
import threading
import time

MILLISECONDS_IN_SECOND = 1000.0
B_IN_MB = 1000000.0
BITS_IN_BYTE = 8.0
RANDOM_SEED = 42
VIDEO_CHUNCK_LEN = 4000.0  # millisec, every time add this amount to buffer
BITRATE_LEVELS = 6
TOTAL_VIDEO_CHUNCK = 48
BUFFER_THRESH = 60.0 * MILLISECONDS_IN_SECOND  # millisec, max buffer limit
DRAIN_BUFFER_SLEEP_TIME = 500.0  # millisec
PACKET_PAYLOAD_PORTION = 0.95
LINK_RTT = 80  # millisec
PACKET_SIZE = 1500  # bytes
VIDEO_SIZE_FILE = './video_size_'
NUM_PATH = 8
PATH_QUEUE_WINDOW = 5


class Path:
    def __init__(self, id):
        self.id = id
        self.rtt = 0
        self.bandwidth = 0
        self.stream_list = []
        self.thread = None
        self.send_times = []

    def setup(self, bw, rtt):
        self.bandwidth = bw
        self.rtt = rtt
        self.stream_list = []

    def close(self):
        self.rtt = 9999

    def assign_stream(self, stream):
        self.stream_list.append(stream)

    def start_thread(self):
        if self.thread is None:
            self.thread = AdaptiveThread(f"Path-{self.id}", self.send_streams)
            self.thread.start()

    def send_streams(self):
        while True:
            self.thread.resume_event.wait()  # Wait for the thread to be resumed
            if self.thread.stop_event.is_set():
                break

            if self.stream_list:
                # Simulate sending a stream
                stream = self.stream_list.pop(0)
                self.send_times.append(stream.length / self.bandwidth)

                if self.is_dropped():  # Check if the path is dropped
                    self.handle_dropped_path(stream)
                    break  # Exit the loop and pause the thread

                print(f"Path {self.id} sent stream {stream.id}")

            else:
                self.thread.pause()  # Pause if no streams are available


    def is_dropped(self):
        # Implement logic to check if the path is dropped
        return self.rtt >= 9999  # Example condition to determine if path is dropped

    def handle_dropped_path(self, remaining_stream):
        # If the path is dropped, return the remaining stream(s) to the main list
        print(f"Path {self.id} dropped. Returning remaining streams to the main list.")
        # Add the remaining stream back to the global stream list (or a specific reassign list)
        global_stream_list.append(remaining_stream)  # Assuming `global_stream_list` is accessible
        # Optionally, add all other remaining streams in `self.stream_list` back to the global list
        while self.stream_list:
            global_stream_list.append(self.stream_list.pop(0))



class Stream:
    def __init__(self, id, length):
        self.id = id
        self.length = length


class AdaptiveThread:
    def __init__(self, name, target):
        self.name = name
        self.resume_event = threading.Event()
        self.stop_event = threading.Event()
        self.resume_event.set()  # Initially set to allow the thread to run
        self.thread = threading.Thread(target=target)
    
    def start(self):
        self.thread.start()

    def pause(self):
        self.resume_event.clear()  # Clear the event, pausing the thread
    
    def resume(self):
        self.resume_event.set()  # Set the event, resuming the thread

    def stop(self):
        self.stop_event.set()  # Signal the thread to stop
        self.resume_event.set()  # Ensure the thread isn't stuck in wait


class Server:
    def __init__(self, all_cooked_time, all_cooked_bw, random_seed=RANDOM_SEED):
        assert len(all_cooked_time) == len(all_cooked_bw)

        np.random.seed(random_seed)

        self.all_cooked_time = all_cooked_time
        self.all_cooked_bw = all_cooked_bw

        self.video_chunk_counter = 0
        self.buffer_size = 0

        # pick a random trace file
        self.trace_idx = 0
        self.cooked_time = self.all_cooked_time[self.trace_idx]
        self.cooked_bw = self.all_cooked_bw[self.trace_idx]

        self.mahimahi_start_ptr = 1
        self.mahimahi_ptr = 1
        self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr - 1]

        self.video_size = {}  # in bytes
        for bitrate in range(BITRATE_LEVELS):
            self.video_size[bitrate] = []
            with open(VIDEO_SIZE_FILE + str(bitrate)) as f:
                for line in f:
                    self.video_size[bitrate].append(int(line.split()[0]))

        self.path_list = [Path(i) for i in range(NUM_PATH)]
        global global_stream_list 
        global time_stamp
        global_stream_list = []

    def monitor_path_change(self):
        """
        This function monitors for any changes in path conditions and updates the path_list.
        """
        self.setup_path()
        while True:
            current_bw = self.cooked_bw[self.mahimahi_ptr]
            current_rtt = [LINK_RTT for _ in range(NUM_PATH)]  # Simplified RTT calculation
            self.update_path(current_bw, current_rtt)

    def setup_path(self):
        for i in range(NUM_PATH):
            self.path_list[i].setup(1, 1)
            self.path_list[i].start_thread()

    def update_path(self, current_bw, current_rtt):
        for i in range(NUM_PATH):
            if current_bw[i] > 0 and current_rtt[i] > 0:
                self.path_list[i].setup(current_bw[i], current_rtt[i])
                self.path_list[i].resume_event.set()
            else:
                self.path_list[i].close()


    def segment(self, chunk_size):

        for i in range(chunk_size // 20000):
            global_stream_list.append(Stream(i, 20000))
        global_stream_list.append(Stream(i + 1, chunk_size % 20000))

    def get_video_chunk(self, quality):
        assert quality >= 0
        assert quality < BITRATE_LEVELS

        video_chunk_size = self.video_size[quality][self.video_chunk_counter]
        self.segment(video_chunk_size)

        delay = 0.0
        video_chunk_counter_sent = 0

        path_monitor_thread = threading.Thread(target=self.monitor_path_change)
        path_monitor_thread.daemon = True
        path_monitor_thread.start()

        while global_stream_list:  # Download video chunk over mahimahi with MPQUIC scheduler
            # Sort paths based on RTT (ascending order)
            self.path_list.sort(key=lambda x: x.rtt)
            time_stamp = max([sum(path.send_times) for path in self.path_list]) if self.path_list[0].send_times else 0
            for path in self.path_list:
                # Check if the path has space in its queue
                if len(path.stream_list) < PATH_QUEUE_WINDOW and sum(path.send_times)<time_stamp:
                    if global_stream_list:
                        path.assign_stream(global_stream_list.pop(0))
                    else:
                        break

        max_delay = 0
        for path in self.path_list:
            if path.send_times:
                path_time = sum(path.send_times)
                if path_time > max_delay:
                    max_delay = path_time

        delay = max_delay * MILLISECONDS_IN_SECOND
        delay += LINK_RTT

        rebuf = np.maximum(delay - self.buffer_size, 0.0)

        self.buffer_size = np.maximum(self.buffer_size - delay, 0.0)
        self.buffer_size += VIDEO_CHUNCK_LEN

        sleep_time = 0
        if self.buffer_size > BUFFER_THRESH:
            drain_buffer_time = self.buffer_size - BUFFER_THRESH
            sleep_time = np.ceil(drain_buffer_time / DRAIN_BUFFER_SLEEP_TIME) * \
                         DRAIN_BUFFER_SLEEP_TIME
            self.buffer_size -= sleep_time

            while True:
                duration = self.cooked_time[self.mahimahi_ptr] \
                           - self.last_mahimahi_time
                if duration > sleep_time / MILLISECONDS_IN_SECOND:
                    self.last_mahimahi_time += sleep_time / MILLISECONDS_IN_SECOND
                    break
                sleep_time -= duration * MILLISECONDS_IN_SECOND
                self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr]
                self.mahimahi_ptr += 1

                if self.mahimahi_ptr >= len(self.cooked_bw):
                    self.mahimahi_ptr = 1
                    self.last_mahimahi_time = 0

        return_buffer_size = self.buffer_size

        self.video_chunk_counter += 1
        video_chunk_remain = TOTAL_VIDEO_CHUNCK - self.video_chunk_counter

        end_of_video = False
        if self.video_chunk_counter >= TOTAL_VIDEO_CHUNCK:
            end_of_video = True
            self.buffer_size = 0
            self.video_chunk_counter = 0
            
            self.trace_idx += 1
            if self.trace_idx >= len(self.all_cooked_time):
                self.trace_idx = 0            

            self.cooked_time = self.all_cooked_time[self.trace_idx]
            self.cooked_bw = self.all_cooked_bw[self.trace_idx]

            self.mahimahi_ptr = self.mahimahi_start_ptr
            self.last_mahimahi_time = self.cooked_time[self.mahimahi_ptr - 1]

        next_video_chunk_sizes = [self.video_size[i][self.video_chunk_counter] for i in range(BITRATE_LEVELS)]

        return delay, \
            sleep_time, \
            return_buffer_size / MILLISECONDS_IN_SECOND, \
            rebuf / MILLISECONDS_IN_SECOND, \
            video_chunk_size, \
            next_video_chunk_sizes, \
            end_of_video, \
            video_chunk_remain

