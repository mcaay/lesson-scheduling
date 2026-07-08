EXAMPLE_SPEC = """lesson blocks
Monday-Thursday 18:00-19:25
Monday-Thursday 19:30-20:55
Monday-Thursday 21:00-22:25

location Swing Studio
rooms 2

location Jazz Loft
rooms 1

instructor Ania
roles follower
prefers minimum 1 class per week
prefers maximum 3 classes per week
can teach LH1, LH2, LH3, Charleston 1, Charleston 2
available Monday-Thursday 17:00-22:30
prefers teaching with Mateusz

instructor Mateusz
roles leader
prefers minimum 1 class per week
prefers maximum 3 classes per week
can teach LH1, LH2, LH3, Charleston 1, Charleston 2
available Monday-Thursday 17:00-22:30
prefers teaching with Ania

instructor Marysia
roles follower, solo
prefers minimum 1 class per week
prefers maximum 3 classes per week
can teach LH1, LH2, LH3, Balboa 1, Balboa 2, Solo Jazz
available Monday-Thursday 17:00-22:30
prefers teaching with Rafał

instructor Rafał
roles leader
prefers minimum 1 class per week
prefers maximum 3 classes per week
can teach LH1, LH2, LH3, Balboa 1, Balboa 2
available Monday-Thursday 17:00-22:30
prefers teaching with Marysia

group LH1
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower

group LH2
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower

group LH3
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower

group Charleston 1
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower

group Balboa 1
needs 1 lesson per week
duration 85 minutes
teacher roles leader, follower

group Solo Jazz
needs 1 lesson per week
duration 85 minutes
teacher roles solo
"""
