"""
Create an interface for bartender2

This is a public version of the bar simulator for distribution
on the web.


-Make executable on windows (compile on wine?)
-Make executable on phone (qpython or py2app?)

Good morning

"""



import random
import simpy

print("Welcome to MAIKO SUSHI LOUNGE. \n"
      "The Bartender has been arrested.\n"
      "YOU are now the bartender.")

BARTENDER_NAME = input('What is your name?\n')

RANDOM_SEED = 42

# Time to complete a sip
PT_MEAN = 3.0

# Stddev of processing time
PT_STD = 2.0

# Mean time it takes a drink to go empty
EMPTY_MEAN = int(input('How many minutes does it take to *DRINK* a cocktail?\n'))

# Poisson param for expovariate
EMPTY_PSSN = 1 / EMPTY_MEAN

# Time it takes to make a drink
POUR_TIME = int(input('How many *SECONDS* does it take you to *MAKE* a drink?\n')) / 60

# Duration of bartender tasks (30 min per OCD point)
TASK_DURATION = int(input('On a scale of 1-5, how OCD are you?\n')) * 20.0

# Number of customers at bar
INITIAL_CUSTOMERS = int(input('How many customers do you want to start with?\n'))

ARRIVAL_FREQUENCY = 30 / int(input('On a scale of 1-5, how busy is the bar?\n'))

SHOT_FREQUENCY = 60 / int(input('On a scale of 1-5, how much do you want to drink?\n'))

# Simulation time in weeks
# WEEKS = 4

# Simulation time in minutes
# SIM_TIME = WEEKS * 7 * 24 * 60
SIM_TIME = int(input('How long is the shift in hours?\n')) * 60


def time_per_sip():
    """Actual time for a specific sip"""
    time = random.normalvariate(PT_MEAN, PT_STD)
    # time can't be negative
    if time < 0:
        time = 0
    return time


def time_to_empty():
    """Return time to next failure for a machine"""
    return random.expovariate(EMPTY_PSSN)


def minutes_to_hours(minutes):
    return float(minutes) / 60


from datetime import datetime, timedelta


def mins_to_hours(minutes):
    """
    Converts a number of minutes to a time of day
    see...
    https://stackoverflow.com/questions/4048651/python-function-to-convert-seconds-into-minutes-hours-and-days
    :param minutes:
    :return:
    """
    delta = timedelta(minutes=int(minutes))
    d = datetime(1, 1, 1, ) + delta
    ret = '%d:%02d' % (d.hour, d.minute)
    return ret


class Customer(object):
    """
    A customer takes sips and finishes a drink at random intervals.

    When the drink is empty, the customer interrupts the bartender.

    """

    def __init__(self, env, name, repairman):
        self.env = env
        self.name = name
        self.sips_taken = 0
        self.needs_drink = False
        self.drunk = False
        self.empty_drinks = 0
        self.empty_time = 0
        self.upset = False
        self.dead = False
        self.in_bar = True

        # Start processes on creation
        print('%s entered the bar at %s.' % (self.name, mins_to_hours(env.now)))
        self.process = env.process(self.drinking(repairman))
        env.process(self.drink_empty())

    def drinking(self, bartender):
        """
        Produces positive reactions until something is needed.

        While having reactions, things are often needed.
        A bartender is requested at that time.

        :param bartender:
        :return:
        """
        while True:
            # Take a sip
            time_left = time_per_sip()
            while time_left:
                try:
                    start = self.env.now
                    yield self.env.timeout(time_left)
                    time_left = 0  # Set to 0 to exit while loop

                except simpy.Interrupt as e:
                    if e.cause == 'left':
                        self.in_bar = False
                        env.exit()
                    # print('%s\'s drink empty at %s ' % (self.name, mins_to_hours(env.now)))
                    self.needs_drink = True
                    self.empty_drinks += 1
                    if self.empty_drinks > 5:
                        self.drunk = True
                    # How much time is left?
                    time_left -= self.env.now - start

                    # Request a bartender, preempting other work
                    with bartender.request(priority=1) as req:
                        try:
                            yield req
                            yield self.env.timeout(POUR_TIME)
                            print('\n%s\'s drink filled at %s ' % (self.name, mins_to_hours(env.now)))
                            wait_time = env.now - self.empty_time
                            print('%s waited %d minutes' % (self.name, wait_time))
                            global drinks
                            drinks += 1
                            if 5 < wait_time < 8:
                                print('%s seems irritated.' % self.name)
                            if 8 < wait_time < 12:
                                print('%s is yelling at the bartender.' % self.name)
                                self.upset = True
                            if 12 < wait_time < 25:
                                print('%s is leaving a negative yelp review.' % self.name)
                                self.upset = True
                                leave(self)
                            if 25 < wait_time:
                                print('%s has died.' % self.name)
                                self.dead = True
                                self.in_bar = False
                                leave(self)
                            print('\n')
                        except simpy.Interrupt as e:
                            if e.cause == 'left':
                                self.in_bar = False
                                env.exit()

                    self.needs_drink = False

            # If no time left, part is done.
            self.sips_taken += 1
            # print('%s drinks at %d' % (self.name, env.now))

    def drink_empty(self):
        """Drink runs out"""
        while True:
            try:
                yield self.env.timeout(time_to_empty())
                if not self.needs_drink and self.in_bar:
                    # If it's not broke, don't break it!
                    # print(self.in_bar)
                    print('%s\'s drink empty at %s ' % (self.name, mins_to_hours(env.now)))
                    self.empty_time = env.now
                    self.process.interrupt()
            except simpy.exceptions.StopProcess as e:
                # to handle process already terminated
                # may not be necessary since if self.in_bar fixed

                env.exit()


tasks = 0
drinks = 0


def other_tasks(env, bartender):
    """The Bartender's tasks which may be interrupted"""
    global tasks

    while True:
        # Start a new job
        done_in = TASK_DURATION
        while done_in:
            # Retry the job until it is done
            with bartender.request(priority=2) as req:
                yield req
                try:
                    print('%s is caught up, resumes cleaning at %s ' % (BARTENDER_NAME, mins_to_hours(env.now)))
                    print('There are %d customers in the bar' % len(customers))
                    # Display progress as a percent
                    print('Cleaning progress: %d percent\n' % (((TASK_DURATION - done_in) / TASK_DURATION) * 100))
                    start = env.now
                    yield env.timeout(done_in)
                    done_in = 0
                except simpy.Interrupt:
                    print('%s makes drink at %s ' % (BARTENDER_NAME, mins_to_hours(env.now)))
                    done_in -= env.now - start

        # If no time left, job completed
        print('%s completed cleaning at %s ' % (BARTENDER_NAME, mins_to_hours(env.now)))
        tasks += 1


customer_names = [
    'Lor', 'Jeremy', 'Ina', 'Dude-bro', 'Bill', 'Tina',
]
random.shuffle(customer_names)

# generate random name for arbitrary number:
import names

# Setup and start the simulation
print('Bartender Simulation')
random.seed(RANDOM_SEED)

# env = simpy.Environment()
env = simpy.rt.RealtimeEnvironment(factor=2)
bartender = simpy.PreemptiveResource(env, capacity=1)
# create initial customers
customers = [Customer(env, names.get_first_name(), bartender)
             for i in range(INITIAL_CUSTOMERS)]
env.process(other_tasks(env, bartender))

shots = 0


# Bartender is offered a shot at random intervals
def take_shot(env):
    global shots
    global POUR_TIME

    while True:
        yield env.timeout(random.expovariate(1 / SHOT_FREQUENCY))
        print("\n**You take a shot with Angie**\n")
        shots += 1
        if shots > 2:
            print('With each shot, %s is making drinks more slowly...\n' % BARTENDER_NAME)
            POUR_TIME += 0.5


# Add a customer at a random interval
def add_customers(env):
    while True:
        yield env.timeout(random.expovariate(1 / ARRIVAL_FREQUENCY))
        customers.append(Customer(env, names.get_first_name(), bartender))


# Customers leave the bar at a random interval
# Don't remove from list, just change state so they won't be served
def remove_customers(env):
    while True:
        yield env.timeout(random.expovariate(1 / 30))
        cust = random.choice(customers)
        if cust.in_bar:
            cust.in_bar = False
            cust.process.interrupt(cause='left')
            print('\n%s has left' % cust.name)
            if cust.upset and not cust.dead:
                print("%s said they're not coming back!!" % cust.name)
            elif cust.dead:
                print("%s was carried out on a stretcher." % cust.name)
            elif cust.drunk:
                print("%s turned red and stumbled out the door." % cust.name)
            else:
                print("%s had a good time.\n" % cust.name)
            print('\n')


def leave(cust):
    if cust.in_bar or cust.dead:
        cust.in_bar = False
        # not allowed to interrupt self
        # cust.process.interrupt(cause='left')
        print('\n%s has left' % cust.name)
        if cust.upset and not cust.dead:
            print("%s said they're not coming back!!" % cust.name)
        elif cust.dead:
            print("%s was carried out on a stretcher." % cust.name)
        elif cust.drunk:
            print("%s turned red and stumbled out the door." % cust.name)
        else:
            print("%s had a good time." % cust.name)
        print('\n')


env.process(add_customers(env))
env.process(remove_customers(env))
env.process(take_shot(env))
# Execute!
env.run(until=SIM_TIME)

# Analysis/results
# print('Machine shop results after %s weeks' % WEEKS)
print("*****Shift Summary*****")

print("\nCustomer Details....")
drunks = 0
upsets = 0
deads = 0
for customer in customers:
    print('%s took %d sips, and finished %d drinks' % (customer.name, customer.sips_taken, customer.empty_drinks))
    if customer.drunk:
        print('%s is drunk.' % customer.name)
        drunks += 1
    if customer.upset:
        print('%s is upset.' % customer.name)
        upsets += 1
    if customer.dead:
        print('%s is dead.' % customer.name)
        deads += 1

print("\nCustomer Summary...")
print('Total customers: %d' % len(customers))
print('Upset customers: %d' % upsets)
if upsets > 3:
    print('%s has been written up for too many upset customers.' % BARTENDER_NAME)

print('Drunk customers: %d' % drunks)

print("\nBartenders.....")
print('%s completed %d tasks and made %d drinks' % (BARTENDER_NAME, tasks, drinks))
if tasks < 1:
    print('%s has been written up for not closing properly.' % BARTENDER_NAME)
else:
    print('%s has lived to bartend another day')
print('%s was paid %d dollars' % (BARTENDER_NAME, (drinks * 1.5)))

print('%d customers died during this shift.' % deads)
