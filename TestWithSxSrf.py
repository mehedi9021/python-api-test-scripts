import logging
import time
import base64
import concurrent.futures
import requests  # type: ignore

# Configuration Variables
API_URL = "https://reqres.in/api/users?page=2"  # Replace with your API URL
NUM_THREADS = 10  # Number of concurrent users (threads) matching JMeter
RAMP_UP_PERIOD = 1  # Ramp-up period in seconds
LOOP_COUNT = 5  # Set to 'inf' for infinite loop or an integer for fixed loops
REQUEST_TYPE = "GET"  # HTTP method: GET, POST, PUT, PATCH, DELETE
SEND_PARAMS = False  # True if sending parameters, False otherwise
BODY_DATA = False  # True if sending body data
SEND_AUTH_TOKEN = False  # Set to True to include Bearer Auth Token in the request header
SEND_SXS_TOKEN = False  # Set to True to include SxSrf Token in the request header
SEND_ORIGIN = False  # Set to True to include Origin header in the request
PARAMS = {}  # Parameters to send if SEND_PARAMS is True
BODY_CONTENT = {}  # JSON body data to send if BODY_DATA is True
AUTH_TOKEN = ""  # Your Bearer Auth token
SXS_TOKEN = ""  # SxSrf token placeholder, will be dynamically updated
HEADERS = {"Content-Type": "application/json"}  # Set content-type to match JMeter
ORIGIN_URL = ""  # Origin URL

# Configure Logging
log_file_name = f"threads_{NUM_THREADS}_loop_{LOOP_COUNT}.log"
logging.basicConfig(
    filename=log_file_name,
    level=logging.INFO,
    format="%(asctime)s [Thread %(thread)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


# Function to send a request
def send_request(thread_id):
    global SXS_TOKEN
    headers = HEADERS.copy()

    # Add Bearer Auth Token if enabled
    if SEND_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    # Add SxSrf Token if enabled
    if SEND_SXS_TOKEN and SXS_TOKEN:
        headers["sxsrf"] = SXS_TOKEN

    # Add Origin header if enabled
    if SEND_ORIGIN:
        headers["Origin"] = ORIGIN_URL

    try:
        start_time = time.time()

        if SEND_PARAMS:
            response = getattr(requests, REQUEST_TYPE.lower())(
                API_URL,
                params=PARAMS if REQUEST_TYPE == "GET" else None,
                json=BODY_CONTENT if BODY_DATA else None,
                headers=headers,
            )
        else:
            response = getattr(requests, REQUEST_TYPE.lower())(
                API_URL,
                json=BODY_CONTENT if BODY_DATA else None,
                headers=headers,
            )

        end_time = time.time()
        execution_time = (end_time - start_time) * 1000
        response_text = response.text.strip()[:500]

        # Log the response and print results for each thread
        if response.status_code == 200:
            log_message = f"[Thread {thread_id}] Passed - Execution Time: {execution_time:.2f} ms, Status Code: {response.status_code}, Response: {response_text}"
            logging.info(log_message)
            print(f"[Thread {thread_id}] Passed - Status Code: {response.status_code}, Response: {response.text}")
        else:
            log_message = f"[Thread {thread_id}] Failed - Status Code: {response.status_code}, Response: {response_text}"
            logging.error(log_message)
            print(f"[Thread {thread_id}] Failed - Status Code: {response.status_code}, Response: {response.text}", end='')

        # Update the SXS token if needed
        if SEND_SXS_TOKEN:
            new_sxs_token = extract_sxs_token(response.headers, response.text)
            if new_sxs_token:
                SXS_TOKEN = new_sxs_token
                logging.info(f"[Thread {thread_id}] Extracted and updated SXS token")

        return response.status_code, execution_time, response.text

    except Exception as e:
        error_message = f"[Thread {thread_id}] Failed - Error: {str(e)}"
        logging.error(error_message)
        print(error_message, end='')  # Display the error on the console without a newline
        return None, None, str(e)


# Function to extract cf-ray-status-id-tn (SXS token) from the response header or body
def extract_sxs_token(response_headers, response_body):
    # Extract from header
    cf_header_value = response_headers.get("cf-ray-status-id-tn", "")
    if cf_header_value:
        encoded = base64.b64encode(cf_header_value.encode("utf-8")).decode("utf-8")
        encoded = base64.b64encode(encoded.encode("utf-8")).decode("utf-8")
        return encoded

    return None


# Function to calculate ramp-up interval
def get_ramp_up_interval():
    if RAMP_UP_PERIOD <= 0 or NUM_THREADS <= 1:
        return 0
    return RAMP_UP_PERIOD / NUM_THREADS


# Load Testing Function
def perform_load_test():
    passed = 0
    failed = 0
    execution_times = []
    total_requests = 0
    total_execution_time = 0  # To store total execution time for throughput calculation

    print(f"Starting load test with ramp-up period of {RAMP_UP_PERIOD} seconds...")
    print(f"Number of Threads: {NUM_THREADS}, Loop Count: {LOOP_COUNT}")
    print(f"Logging results to: {log_file_name}")

    ramp_up_interval = get_ramp_up_interval()

    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = []

        if LOOP_COUNT == "inf":
            # Run indefinitely
            print("Running indefinitely... Press Ctrl+C to stop.")
            while True:
                for thread_id in range(NUM_THREADS):
                    futures.append(executor.submit(send_request, thread_id))
                    total_requests += 1
                if ramp_up_interval > 0:
                    time.sleep(ramp_up_interval)

                for future in concurrent.futures.as_completed(futures):
                    status_code, execution_time, response_text = future.result()

                    # Output and log each thread's result
                    if status_code in [200, 201] and execution_time is not None:
                        passed += 1
                        execution_times.append(execution_time)
                        total_execution_time += execution_time / 1000  # Convert to seconds for throughput calculation
                        print(f"[Thread {thread_id}] Passed - Status Code: {status_code}, Response: {response_text}", end='')
                    else:
                        failed += 1
                        print(f"[Thread {thread_id}] Failed - Status Code: {status_code}, Response: {response_text}", end='')

        else:
            loop = range(LOOP_COUNT)
            for _ in loop:
                for thread_id in range(NUM_THREADS):
                    futures.append(executor.submit(send_request, thread_id))
                    total_requests += 1
                if ramp_up_interval > 0:
                    time.sleep(ramp_up_interval)

            for future in concurrent.futures.as_completed(futures):
                status_code, execution_time, response_text = future.result()

                # Output and log each thread's result
                if status_code in [200, 201] and execution_time is not None:
                    passed += 1
                    execution_times.append(execution_time)
                    total_execution_time += execution_time / 1000  # Convert to seconds for throughput calculation
                    print(f"[Thread {thread_id}] Passed - Status Code: {status_code}, Response: {response_text}", end='')
                else:
                    failed += 1
                    print(f"[Thread {thread_id}] Failed - Status Code: {status_code}, Response: {response_text}", end='')

    if execution_times:
        min_time = min(execution_times)
        max_time = max(execution_times)
        avg_time = sum(execution_times) / len(execution_times)
    else:
        min_time = max_time = avg_time = None

    error_percentage = (failed / total_requests) * 100 if total_requests > 0 else 0
    throughput = total_requests / total_execution_time if total_execution_time > 0 else 0  # Requests per second

    print("\n--- Load Test Results ---")
    print(f"API URL: {API_URL}")
    print(f"HTTP Method: {REQUEST_TYPE}")
    print(f"Number of Threads: {NUM_THREADS}")
    print(f"Ramp-Up Period: {RAMP_UP_PERIOD} seconds")
    print(f"Loop Count: {LOOP_COUNT}")
    print(f"Total Executions: {total_requests}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Error Percentage: {error_percentage:.2f}%")
    print(f"Min Execution Time: {min_time:.2f} ms" if min_time is not None else "Min Execution Time: N/A")
    print(f"Max Execution Time: {max_time:.2f} ms" if max_time is not None else "Max Execution Time: N/A")
    print(f"Average Execution Time: {avg_time:.2f} ms" if avg_time is not None else "Average Execution Time: N/A")
    print(f"Throughput: {throughput:.2f} requests/second")

    logging.info("\n--- Load Test Results ---")
    logging.info(f"API URL: {API_URL}")
    logging.info(f"HTTP Method: {REQUEST_TYPE}")
    logging.info(f"Number of Threads: {NUM_THREADS}")
    logging.info(f"Ramp-Up Period: {RAMP_UP_PERIOD} seconds")
    logging.info(f"Loop Count: {LOOP_COUNT}")
    logging.info(f"Total Executions: {total_requests}")
    logging.info(f"Passed: {passed}")
    logging.info(f"Failed: {failed}")
    logging.info(f"Error Percentage: {error_percentage:.2f}%")
    logging.info(f"Min Execution Time: {min_time:.2f} ms" if min_time is not None else "Min Execution Time: N/A")
    logging.info(f"Max Execution Time: {max_time:.2f} ms" if max_time is not None else "Max Execution Time: N/A")
    logging.info(
        f"Average Execution Time: {avg_time:.2f} ms" if avg_time is not None else "Average Execution Time: N/A")
    logging.info(f"Throughput: {throughput:.2f} requests/second")
    logging.info("\n------------- End -------------")


if __name__ == "__main__":
    perform_load_test()
