import datetime
import os.path
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# If modifying these SCOPES, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Define file paths - these assume main.py (and thus CWD) is in the project root
# and credentials.json/token.json are also in the root.
CREDENTIALS_FILE = "credentials.json" # Should be in the project root
TOKEN_FILE = "token.json" # Will be created in the project root after first auth

class GoogleCalendarService:
    """Handles interactions with the Google Calendar API."""

    def __init__(self):
        self.service = self._get_calendar_service()

    def _get_calendar_service(self):
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first time.
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
                logger.info("Loaded credentials from token.json")
            except Exception as e:
                logger.error(f"Error loading credentials from {TOKEN_FILE}: {e}. Will attempt re-authentication.")
                creds = None
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Credentials expired, attempting to refresh...")
                    creds.refresh(Request())
                    logger.info("Credentials refreshed successfully.")
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}. Need to re-authorize.")
                    creds = None # Force re-authentication
            else:
                logger.info("Valid credentials not found or no refresh token. Starting OAuth flow.")
                if not os.path.exists(CREDENTIALS_FILE):
                    logger.critical(f"{CREDENTIALS_FILE} not found. Please download it from GCP and place it in the project root.")
                    raise FileNotFoundError(f"{CREDENTIALS_FILE} not found. Cannot authenticate with Google Calendar.")
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                    # port=0 means the OS will pick an available port.
                    # If you have issues with browser opening, you might need to specify a fixed port
                    # and ensure your GCP OAuth consent screen has it in authorized redirect URIs (for web apps).
                    # For "Desktop app" type, this is usually handled well by a local redirect.
                    creds = flow.run_local_server(port=0)
                    logger.info("OAuth flow completed. Credentials obtained.")
                except Exception as e:
                    logger.critical(f"Error during OAuth flow: {e}", exc_info=True)
                    raise
            
            # Save the credentials for the next run
            try:
                with open(TOKEN_FILE, "w") as token:
                    token.write(creds.to_json())
                logger.info(f"Credentials saved to {TOKEN_FILE}")
            except Exception as e:
                logger.error(f"Error saving credentials to {TOKEN_FILE}: {e}", exc_info=True)
        
        if not creds:
             logger.critical("Failed to obtain valid credentials for Google Calendar.")
             raise ConnectionRefusedError("Could not get Google Calendar credentials.")

        try:
            service = build("calendar", "v3", credentials=creds)
            logger.info("Google Calendar service built successfully.")
            return service
        except HttpError as error:
            logger.error(f"An error occurred building the calendar service: {error}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred building the calendar service: {e}", exc_info=True)
            return None

    def list_events(self, max_results=10, calendar_id='primary'):
        """Lists the next upcoming events on the user's calendar."""
        if not self.service:
            logger.error("Calendar service not available.")
            return "Error: Calendar service not initialized."
        try:
            now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
            logger.info(f"Getting up to {max_results} upcoming events from calendar: {calendar_id}")
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=now,
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            if not events:
                logger.info("No upcoming events found.")
                return "No upcoming events found."
            
            event_list_str = "Upcoming events:\n"
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                event_list_str += f"- {start}: {event['summary']}\n"
            logger.info(f"Found {len(events)} events.")
            return event_list_str

        except HttpError as error:
            logger.error(f"An API error occurred while listing events: {error}")
            return f"An API error occurred: {error}"
        except Exception as e:
            logger.error(f"An unexpected error occurred while listing events: {e}", exc_info=True)
            return f"An unexpected error occurred: {e}"

    def create_event(self, summary: str, start_time: str, end_time: str, calendar_id='primary', timezone='UTC'):
        """Creates an event on the user's calendar.
        start_time and end_time should be in ISO format, e.g., '2024-06-15T10:00:00'
        timezone example: 'America/Los_Angeles', 'Europe/London', or default 'UTC'.
        """
        if not self.service:
            logger.error("Calendar service not available.")
            return "Error: Calendar service not initialized."
        
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time,
                'timeZone': timezone,
            },
        }
        try:
            logger.info(f"Creating event: {summary} from {start_time} to {end_time} in {timezone}")
            created_event = self.service.events().insert(calendarId=calendar_id, body=event).execute()
            logger.info(f"Event created: {created_event.get('htmlLink')}")
            return f"Event created: {summary} - Link: {created_event.get('htmlLink')}"
        except HttpError as error:
            logger.error(f"An API error occurred while creating event: {error}")
            return f"An API error occurred creating event: {error}"
        except Exception as e:
            logger.error(f"An unexpected error occurred while creating event: {e}", exc_info=True)
            return f"An unexpected error occurred creating event: {e}"

    def delete_event(self, event_id: str, calendar_id='primary'):
        """Deletes an event from the user's calendar."""
        if not self.service:
            logger.error("Calendar service not available.")
            return "Error: Calendar service not initialized."
        try:
            logger.info(f"Deleting event ID: {event_id} from calendar: {calendar_id}")
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            logger.info(f"Event ID: {event_id} deleted successfully.")
            return f"Event ID: {event_id} deleted successfully."
        except HttpError as error:
            if error.resp.status == 404:
                logger.warning(f"Event ID: {event_id} not found for deletion.")
                return f"Event ID: {event_id} not found."
            logger.error(f"An API error occurred while deleting event: {error}")
            return f"An API error occurred deleting event: {error}"
        except Exception as e:
            logger.error(f"An unexpected error occurred while deleting event: {e}", exc_info=True)
            return f"An unexpected error occurred deleting event: {e}"

# Example usage (for testing this module directly):
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("Testing GoogleCalendarService...")
    try:
        calendar_service = GoogleCalendarService()
        if calendar_service.service:
            print("\n--- Listing upcoming events ---")
            print(calendar_service.list_events(max_results=5))
            
            # # Example: Create an event (uncomment to test)
            # print("\n--- Creating a test event ---")
            # start_iso = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat()
            # end_iso = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1, hours=1)).isoformat()
            # create_response = calendar_service.create_event(
            #     summary="Test Event from SlackBot",
            #     start_time=start_iso,
            #     end_time=end_iso,
            #     timezone='UTC' # Or your local timezone like 'Europe/Amsterdam'
            # )
            # print(create_response)

            # # Example: Delete an event (you'll need an eventId)
            # print("\n--- Deleting an event ---")
            # event_id_to_delete = "YOUR_EVENT_ID_HERE" # Replace with an actual event ID
            # if event_id_to_delete != "YOUR_EVENT_ID_HERE":
            #     print(calendar_service.delete_event(event_id_to_delete))
            # else:
            #     print("Skipping delete test as event_id_to_delete is not set.")

        else:
            print("Failed to initialize Google Calendar service.")
    except FileNotFoundError as fnf_error:
        print(f"CRITICAL: {fnf_error} - Ensure credentials.json is in the project root.")
    except ConnectionRefusedError as cr_error:
        print(f"CRITICAL: {cr_error} - Could not authenticate/connect to Google Calendar.")
    except Exception as main_err:
        print(f"An error occurred during testing: {main_err}") 