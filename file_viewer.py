import streamlit as st
from streamlit_autorefresh import st_autorefresh
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from pathlib import Path
import pandas as pd
import queue
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime, timedelta
import yaml
import os

# Configure logging
logging.basicConfig(
    filename='file_monitor.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# Define FileEventWrapper
class FileEventWrapper:
    def __init__(self, event):
        self.event_type = event.event_type
        self.src_path = event.src_path
        self.timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def to_dict(self):
        return {
            "event_type": self.event_type,
            "src_path": self.src_path,
            "timestamp": self.timestamp
        }


# Define the event handler for watchdog
class FileEventHandler(FileSystemEventHandler):
    def __init__(self, event_queue):
        super().__init__()
        self.event_queue = event_queue

    def on_any_event(self, event):
        if not event.is_directory and not any(ignored in event.src_path for ignored in [".DS_Store", ".localized"]):
            wrapped_event = FileEventWrapper(event)
            self.event_queue.put(wrapped_event)
            logging.info(
                f"Event detected: {wrapped_event.event_type} - {wrapped_event.src_path} at {wrapped_event.timestamp}")


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


# Function to load configuration
def load_config():
    config_path = Path(".file_viewer.yaml")
    if config_path.exists():
        with open(config_path, "r") as file:
            return yaml.safe_load(file)
    return {"refresh_rate": 15000, "starting_directory": "~/Downloads"}


config = load_config()

# Initialize session state
if 'event_queue' not in st.session_state:
    st.session_state.event_queue = queue.Queue()
if 'observer' not in st.session_state:
    st.session_state.observer = None
if 'event_list' not in st.session_state:
    st.session_state.event_list = []
if 'monitoring' not in st.session_state:
    st.session_state.monitoring = False


# Function to display the file listing as a tree view
def display_file_listing_as_tree(folder_path, ui):
    with ui.container():
        st.subheader("Current Directory Contents")
        if os.path.exists(folder_path):
            files_data = []
            for file in Path(folder_path).iterdir():
                if file.name not in [".DS_Store", ".localized"]:
                    files_data.append({
                        "file_name": file.name,
                        "file_type": "Folder" if file.is_dir() else "File",
                        "modified_time": datetime.fromtimestamp(file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        "size": file.stat().st_size,
                        "path": str(file)
                    })

            grid_options = GridOptionsBuilder.from_dataframe(pd.DataFrame(files_data))
            grid_options.configure_column("path", hide=True)
            AgGrid(pd.DataFrame(files_data), gridOptions=grid_options.build())
        else:
            st.error("The specified folder path does not exist.")


# Function to display recent file events
def display_recent_events(new_events):
    with new_events:
        st.subheader("New Events")
        if st.session_state.event_list:
            cutoff_time = datetime.now() - timedelta(minutes=5)
            recent_events = [
                event.to_dict() for event in st.session_state.event_list
                if datetime.strptime(event.timestamp, '%Y-%m-%d %H:%M:%S') >= cutoff_time
            ]

            if recent_events:
                st.dataframe(pd.DataFrame(recent_events))
            else:
                st.info("No events in the last 5 minutes.")


# Function to display the latest file
def display_latest_file(folder_path, ui):
    with ui:
        st.subheader("Latest File")
        if os.path.exists(folder_path):
            # Filter out .DS_Store and .localized files
            valid_files = [file for file in Path(folder_path).iterdir()
                           if file.name not in [".DS_Store", ".localized"]]
            if not valid_files:
                st.warning("No valid files found in the directory.")
                return

            # Get the most recently modified file
            latest_file = max(valid_files, key=os.path.getmtime)
            if latest_file.suffix in ['.java']:
                st.code(latest_file.read_text(), language='java')
            elif latest_file.suffix in ['.ts']:
                st.code(latest_file.read_text(), language='typescript')
            elif latest_file.suffix in ['.js']:
                st.code(latest_file.read_text(), language='javascript')
            elif latest_file.suffix in ['.py']:
                st.code(latest_file.read_text(), language='python')
            elif latest_file.suffix in ['.sh']:
                st.code(latest_file.read_text(), language='bash')
            elif latest_file.suffix in ['.md']:
                st.markdown(latest_file.read_text())
            elif latest_file.suffix in ['.csv']:
                st.subheader(f"Preview of {latest_file.name}")
                try:
                    df = pd.read_csv(latest_file)
                    st.dataframe(df)
                except Exception as e:
                    st.error(f"Error reading CSV file: {e}")
            elif latest_file.suffix in ['.jpg', '.png', '.webp']:
                st.image(str(latest_file))
            elif latest_file.suffix in ['.mp3', '.wav']:
                st.audio(str(latest_file))
            elif latest_file.suffix in ['.mp4', '.avi']:
                st.video(str(latest_file))
            else:
                st.write({
                    "File Name": latest_file.name,
                    "Size (bytes)": latest_file.stat().st_size,
                    "Modified": datetime.fromtimestamp(latest_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
        else:
            st.error("The specified folder path does not exist.")


def check_events_and_update():
    # Process all events in the queue
    events_processed = False
    while not st.session_state.event_queue.empty():
        event = st.session_state.event_queue.get()
        st.session_state.event_list.append(event)
        events_processed = True

    logging.info(f"Processing events: {len(st.session_state.event_list)}")
    return events_processed


# Main function
def main():
    st.title("Enhanced Real-Time File Viewer")



    # Only check events and update if monitoring is active
    if 'monitoring' in st.session_state and st.session_state.monitoring:
        check_events_and_update()

    # Folder selection and validation
    folder_path = st.text_input("Enter the folder path to monitor:", value=config['starting_directory'])

    folder_path = os.path.expanduser(folder_path)

    if not folder_path or not os.path.exists(folder_path):
        st.error("Please enter a valid folder path.")
        st.stop()

    # Monitoring controls
    col1, col2 = st.columns([2, 1])
    with col1:
        if not st.session_state.monitoring:
            if st.button("Start Monitoring", use_container_width=True):
                st.session_state.observer = start_observer(folder_path, st.session_state.event_queue)
                st.session_state.monitoring = True
                st.success(f"Started monitoring {folder_path}")
        else:
            if st.button("Stop Monitoring", use_container_width=True):
                if st.session_state.observer:
                    stop_observer(st.session_state.observer)
                    st.session_state.observer = None
                st.session_state.monitoring = False
                st.success("Stopped monitoring")
        # Adjust refresh rate
    refresh_interval = st.slider("Set Refresh Interval (ms)", min_value=500, max_value=30000,
                                 value=config['refresh_rate'])
    st_autorefresh(interval=refresh_interval, key="refresh_area")

    refresh_area = st.container()

    with refresh_area:
        new_events = st.empty()
        file_monitor_refresh = st.empty()
        latest_file_ui = st.empty()



    # Display areas
    display_recent_events(new_events)

    display_file_listing_as_tree(folder_path, file_monitor_refresh)

    display_latest_file(folder_path, latest_file_ui.container())


if __name__ == "__main__":
    main()
