import concurrent.futures
import logging
import time
from itertools import count
import requests

# Configuration Variables
API_URL = "https://reqres.in/api/users?page=2"  # Replace with your API URL
NUM_THREADS = 4  # Number of concurrent users (threads) matching JMeter
RAMP_UP_PERIOD = 1  # Ramp-up period in seconds
LOOP_COUNT = 3  # Set to 'inf' for infinite loop or an integer for fixed loops
REQUEST_TYPE = "GET"  # HTTP method: GET, POST, PUT, PATCH, DELETE
SEND_PARAMS = False  # True if sending parameters, False otherwise
BODY_DATA = False  # True if sending body data
SEND_AUTH_TOKEN = False  # Set to True to include Bearer Auth Token in the request header
SEND_SXS_TOKEN = False  # Set to True to include SxSrf Token in the request header
SEND_ORIGIN = False  # Set to True to include Origin header in the request
PARAMS = {"key": "value"}  # Parameters to send if SEND_PARAMS is True
BODY_CONTENT = {"name": "morpheus"}  # JSON body data to send if BODY_DATA is True
AUTH_TOKEN = "your_bearer_auth_token"  # Your Bearer Auth token
SXS_TOKEN = "your_sxsrf_token"  # Your SxSrf token
HEADERS = {"Content-Type": "application/json"}  # Basic headers, modify as needed
ORIGIN_URL = ""  # Origin URL (adjust as needed)

# Configure Logging
log_file_name = f"threads_{NUM_THREADS}_loop_{LOOP_COUNT}.log"
logging.basicConfig(
    filename=log_file_name,
    level=logging.INFO,
    format="%(asctime)s [Thread %(thread)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def send_request(thread_id):
    headers = HEADERS.copy()
    if SEND_AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    if SEND_SXS_TOKEN:
        headers["Sxsrf"] = SXS_TOKEN
    if SEND_ORIGIN:
        headers["Origin"] = ORIGIN_URL

    try:
        start_time = time.time()
        response = getattr(requests, REQUEST_TYPE.lower())(
            API_URL,
            params=PARAMS if SEND_PARAMS and REQUEST_TYPE == "GET" else None,
            json=BODY_CONTENT if BODY_DATA else None,
            headers=headers,
        )
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
        response_text = response.text.strip()[:500]
        logging.info(
            f"[Thread {thread_id}] Success - Execution Time: {execution_time:.2f} ms, Status: {response.status_code}, Response: {response_text}")
        print(f"[Thread {thread_id}] Response Code: {response.status_code}, Response: {response_text}")
        return response.status_code, execution_time, response_text
    except Exception as e:
        logging.error(f"[Thread {thread_id}] Failed - Error: {str(e)}")
        print(f"[Thread {thread_id}] Error: {str(e)}")
        return None, None, str(e)


def perform_load_test():
    print(f"Starting load test with {NUM_THREADS} threads in {RAMP_UP_PERIOD} seconds...")
    ramp_up_interval = RAMP_UP_PERIOD / NUM_THREADS if NUM_THREADS > 1 else 0

    passed, failed, execution_times, total_requests = 0, 0, [], 0
    total_execution_time = 0  # Track total execution time for throughput calculation

    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        loop = count(1) if LOOP_COUNT == "inf" else range(LOOP_COUNT)
        futures = []

        for _ in loop:
            for thread_id in range(NUM_THREADS):
                futures.append(executor.submit(send_request, thread_id))
                total_requests += 1
                time.sleep(ramp_up_interval)  # Ensures all requests are sent within RAMP_UP_PERIOD

            if LOOP_COUNT != "inf" and total_requests >= NUM_THREADS * LOOP_COUNT:
                break

        for future in concurrent.futures.as_completed(futures):
            status_code, execution_time, _ = future.result()
            if status_code in [200, 201] and execution_time is not None:
                passed += 1
                execution_times.append(execution_time)
                total_execution_time += execution_time / 1000  # Accumulate execution time in seconds
            else:
                failed += 1

    min_time = min(execution_times, default=None)
    max_time = max(execution_times, default=None)
    avg_time = sum(execution_times) / len(execution_times) if execution_times else None
    error_percentage = (failed / total_requests) * 100 if total_requests > 0 else 0
    throughput = total_requests / total_execution_time if total_execution_time > 0 else 0  # Requests per second

    # Print results
    print("\n--- Load Test Results ---")
    print(f"API URL: {API_URL}")
    print(f"HTTP Method: {REQUEST_TYPE}")
    print(f"Max Threads: {NUM_THREADS}")
    print(f"Ramp-Up Period: {RAMP_UP_PERIOD} seconds")
    print(f"Loop Count: {'Infinity' if LOOP_COUNT == 'inf' else LOOP_COUNT}")
    print(f"Total Executions: {total_requests}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Error Percentage: {error_percentage:.2f}%")
    print(f"Min Execution Time: {min_time:.2f} ms" if min_time is not None else "Min Execution Time: N/A")
    print(f"Max Execution Time: {max_time:.2f} ms" if max_time is not None else "Max Execution Time: N/A")
    print(f"Average Execution Time: {avg_time:.2f} ms" if avg_time is not None else "Average Execution Time: N/A")
    print(f"Throughput: {throughput:.2f} requests/second")

    # Log summary to the file
    logging.info("\n--- Load Test Results ---")
    logging.info(f"API URL: {API_URL}")
    logging.info(f"HTTP Method: {REQUEST_TYPE}")
    logging.info(f"Max Threads: {NUM_THREADS}")
    logging.info(f"Ramp-Up Period: {RAMP_UP_PERIOD} seconds")
    logging.info(f"Loop Count: {'Infinity' if LOOP_COUNT == 'inf' else LOOP_COUNT}")
    logging.info(f"Total Executions: {total_requests}")
    logging.info(f"Passed: {passed}")
    logging.info(f"Failed: {failed}")
    logging.info(f"Error Percentage: {error_percentage:.2f}%")
    logging.info(f"Min Execution Time: {min_time:.2f} ms" if min_time is not None else "Min Execution Time: N/A")
    logging.info(f"Max Execution Time: {max_time:.2f} ms" if max_time is not None else "Max Execution Time: N/A")
    logging.info(
        f"Average Execution Time: {avg_time:.2f} ms" if avg_time is not None else "Average Execution Time: N/A")
    logging.info(f"Throughput: {throughput:.2f} requests/second")


if __name__ == "__main__":
    perform_load_test()
