import simpy
import random
import statistics

# --- Simulation Parameters ---
# Using the busy airport example
LAMBDA_ARRIVAL = 50.0  # Passengers per minute
MEAN_ID_CHECK = 0.75   # minutes
MIN_SCAN_TIME = 0.5    # minutes
MAX_SCAN_TIME = 1.0    # minutes
SIM_TIME = 300       # minutes to simulate
TARGET_TIME = 15.0     # minutes (average system time goal)

# A list to store the total time each passenger spends in the system
total_system_times = []

class AirportSecurity:
    """Two-stage security checkpoint."""

    def __init__(self, env, num_id_checkers, num_scanners):
        self.env = env
        # The ID check station is a single queue with multiple checkers
        self.id_check_station = simpy.Resource(env, capacity=num_id_checkers)
        # The personal scanners are separate queues, so we model them as a list of resources
        self.scanner_stations = [simpy.Resource(env, capacity=1) for _ in range(num_scanners)]

    def check_id(self, passenger_name):
        """Simulates the time taken for ID and boarding pass check."""
        service_time = random.expovariate(1.0 / MEAN_ID_CHECK)
        yield self.env.timeout(service_time)

    def scan_person(self, passenger_name):
        """Simulates the time taken for the personal body scan."""
        service_time = random.uniform(MIN_SCAN_TIME, MAX_SCAN_TIME)
        yield self.env.timeout(service_time)

def passenger_process(env, name, airport):
    """
    The process a passenger goes through.
    1. Arrives at the security checkpoint.
    2. Gets in line and gets ID checked.
    3. Chooses the shortest line for the personal scanner.
    4. Gets in line and gets scanned.
    5. Exits the system.
    """
    arrival_time = env.now
    # print(f"{arrival_time:.2f}: {name} has arrived at security.")

    # 1. Queue for ID/Boarding Pass Check
    with airport.id_check_station.request() as request:
        yield request
        # print(f"{env.now:.2f}: {name} is at the ID check.")
        yield env.process(airport.check_id(name))

    # 2. Choose the shortest personal scanner queue
    queue_lengths = [len(scanner.queue) for scanner in airport.scanner_stations]
    best_queue_index = queue_lengths.index(min(queue_lengths))
    chosen_scanner = airport.scanner_stations[best_queue_index]
    # print(f"{env.now:.2f}: {name} chose scanner #{best_queue_index + 1}.")

    # 3. Queue for the chosen personal scanner
    with chosen_scanner.request() as request:
        yield request
        # print(f"{env.now:.2f}: {name} is at the scanner.")
        yield env.process(airport.scan_person(name))

    # 4. Record total time in system
    departure_time = env.now
    time_in_system = departure_time - arrival_time
    total_system_times.append(time_in_system)
    # print(f"{departure_time:.2f}: {name} has cleared security in {time_in_system:.2f} minutes.")

def passenger_generator(env, airport):
    """Generates passengers who arrive at the airport."""
    passenger_id = 0
    while True:
        # Calculate the time until the next passenger arrives (Poisson)
        time_to_next_arrival = random.expovariate(LAMBDA_ARRIVAL)
        yield env.timeout(time_to_next_arrival)

        passenger_id += 1
        name = f"Passenger {passenger_id}"
        # Start the process for the new passenger
        env.process(passenger_process(env, name, airport))


# --- Main Experiment ---
if __name__ == "__main__":
    print("--- Airport Security Simulation ---")
    print(f"Goal: Find configurations with average system time < {TARGET_TIME:.2f} minutes.")
    print("=" * 40)

    # We will test a range of configurations for checkers and scanners
    max_checkers_to_test = 50
    max_scanners_to_test = 60
   
    # Store viable solutions
    solutions = []

    # Iterate through different numbers of ID checkers
    for checkers in range(30, max_checkers_to_test + 1):
        # For each number of checkers, iterate through numbers of scanners
        for scanners in range(30, max_scanners_to_test + 1):
           
            # --- Run the simulation for the current configuration ---
            random.seed(42) # for reproducibility
            total_system_times.clear() # Reset stats for new run

            # Set up the environment and start the simulation
            env = simpy.Environment()
            airport = AirportSecurity(env, num_id_checkers=checkers, num_scanners=scanners)
            env.process(passenger_generator(env, airport))
            env.run(until=SIM_TIME)

            # --- Analyze and report results ---
            if total_system_times:
                avg_time = statistics.mean(total_system_times)
                max_time = max(total_system_times)
               
                print(f"Checkers: {checkers}, Scanners: {scanners} -> Avg Time: {avg_time:.2f} min, Max Time: {max_time:.2f} min")

                if avg_time < TARGET_TIME:
                    solutions.append({'checkers': checkers, 'scanners': scanners, 'avg_time': avg_time, 'total_staff': checkers + scanners})
            else:
                 print(f"Checkers: {checkers}, Scanners: {scanners} -> No passengers completed.")

    print("\n" + "=" * 40)
    print("Analysis of Viable Solutions (Avg Time < 15 minutes)")
    print("=" * 40)

    if not solutions:
        print("No viable solutions found in the tested range.")
        print("Try increasing the number of checkers/scanners or the simulation time.")
    else:
        # Find the solution with the minimum total staff
        best_solution = min(solutions, key=lambda x: x['total_staff'])
        print("Viable configurations found:")
        for sol in solutions:
             print(f" -> {sol['checkers']} checkers, {sol['scanners']} scanners (Total: {sol['total_staff']}) | Avg Time: {sol['avg_time']:.2f} min")
       
        print("\n--- Recommendation ---")
        print(f"The most cost-effective solution found is:")
        print(f"  ID/Boarding-Pass Checkers: {best_solution['checkers']}")
        print(f"  Personal-Check Scanners:  {best_solution['scanners']}")
        print(f"  Total Staff:              {best_solution['total_staff']}")
        print(f"  Resulting Average Time:   {best_solution['avg_time']:.2f} minutes")

