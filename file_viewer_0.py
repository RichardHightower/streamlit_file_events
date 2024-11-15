import streamlit as st
from streamlit_autorefresh import st_autorefresh
import os
from pathlib import Path
import queue
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    filename='file_monitor.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Define the event handler for watchdog
class FileEventHandler(FileSystemEventHandler):
    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def on_any_event(self, event):
        if not event.is_directory:
            self.event_queue.put(event)
            logging.info(f"Event detected: {event.event_type} - {event.src_path}")

# Function to start the watchdog observer
def start_observer(path, event_queue):
    logging.info("Starting observer")
    event_handler = FileEventHandler(event_queue)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    logging.info("Observer started")
    return observer

# Function to stop the watchdog observer
def stop_observer(observer):
    logging.info("Stopping observer")
    observer.stop()
    observer.join()
    logging.info("Observer stopped")

# Function to display the file listing
def display_file_listing(folder_path, ui_component):
    with ui_component.container():
        logging.debug("Processing events 2")
        st.subheader("Current Directory Contents")
        if os.path.exists(folder_path):
            files = sorted(Path(folder_path).iterdir(), key=os.path.getmtime, reverse=True)
            for file in files:
                logging.debug(f"Processing file {file}")
                if file.is_file():
                    logging.debug(f"Calling st.text {file}")
                    st.text(f"📄 {file.name}")
        else:
            st.error("The specified folder path does not exist.")

def display_new_events(folder_path, ui_component):
    with ui_component.container():
        logging.debug("Processing events 2")
        st.subheader("New Events")
        for event in st.session_state.event_list :
            st.text(f"New event: {event.event_type} - {event.src_path}")


# Initialize a global queue and observer
if 'event_queue' not in st.session_state:
    st.session_state.event_queue = queue.Queue()
if 'observer' not in st.session_state:
    st.session_state.observer = None
if 'event_list' not in st.session_state:
    st.session_state.event_list = []

def main():
    st.title("Real-Time File Viewer with Streamlit")
    logging.info("Starting Real-Time File Viewer")

    # Folder selection with validation
    folder_path = st.text_input(
        "Enter folder path to monitor",
        value=os.path.expanduser("~/Downloads")
    )

    logging.info(folder_path)
    if not folder_path:
        folder_path = "~/Downloads"

    if not os.path.exists(folder_path):
        st.error("Please enter a valid folder path.")
        logging.info("Invalid folder path")
        st.stop()

    # Monitoring controls
    col1, col2 = st.columns([2, 1])

    with col1:
        if 'monitoring' not in st.session_state or not st.session_state.monitoring:
            if st.button("Start Monitoring", use_container_width=True):
                st.session_state.observer = start_observer(folder_path, st.session_state.event_queue)
                st.session_state.monitoring = True
                st.success(f"Started monitoring {folder_path}")
                logging.info(f"Started monitoring {folder_path}")
        else:
            if st.button("Stop Monitoring", use_container_width=True):
                if st.session_state.observer:
                    stop_observer(st.session_state.observer)
                    st.session_state.observer = None
                st.session_state.monitoring = False
                st.success("Stopped monitoring")
                logging.info("Stopped monitoring")

    refresh_area = st.container()

    with refresh_area:
        new_events = st.empty()
        file_monitor_refresh = st.empty()

    # Check the event queue and update the file listing if there are events
    def check_events_and_update():
        # Process all events in the queue
        events_processed = False
        while not st.session_state.event_queue.empty():
            event = st.session_state.event_queue.get()
            st.session_state.event_list.append(event)
            events_processed = True

        logging.info(f"Processing events: {len(st.session_state.event_list)}")

    # Set the refresh interval (in milliseconds)
    refresh_interval = 15000  # Adjust as needed (e.g., 500 milliseconds = 0.5 seconds)

    # Autorefresh the app
    st_autorefresh(interval=refresh_interval, key="refresh_area")

    # Only check events and update if monitoring is active
    if 'monitoring' in st.session_state and st.session_state.monitoring:
        check_events_and_update()

    display_new_events(folder_path, new_events)
    display_file_listing(folder_path, file_monitor_refresh)


if __name__ == "__main__":
    main()
