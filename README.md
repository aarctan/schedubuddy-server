# schedubuddy-server

This program is the server back-end of [schedubuddy](https://schedubuddy.com/), a schedule generator for the [University of Alberta](https://www.ualberta.ca/index.html).
This program queries a local database that is constructed and updated by utility functions in the util folder of this repository.
Raw data is then processed to generate several schedules for a queried list of courses, and then ranked/filtered by various user-provided metrics.
This is useful for when a student knows the courses they wish to take, and wants to create an optimal schedule.

## API

### Objects
There are three important objects that every endpoint is concerned with.
Term objects describe an academic term by name, dates, and the term ID.
The API will return all terms in the local database, however, when the database is being constructed/updated, it will only fetch ongoing or future terms.
The course object describes a course with various useful attributes (see examples).
Note that this object does not include class times because a course by itself is distinct from a class.
The class object is that which contains class time, instructor, location, and other class-specific information.
Please see the [wiki](https://github.com/Exanut/schedubuddy-server/wiki/API-Objects) for examples of all these objects.

### Endpoints

There are three endpoints that the current version of [schedubuddy](https://schedubuddy.com/) uses.
Upon loading the website, term data is requested to allow the user to select a term in which to use schedubuddy for.
When a term is selected, all the courses available for that course are requested so the user can select their course list.
Please see the [wiki](https://github.com/Exanut/schedubuddy-server/wiki/API-Endpoints) for documentation on these endpoints.

## Schedule generation

This section is a brief overview of the schedule generation algorithm -- refer to the source code for implementation.

A "valid" schedule is considered to be one that has no time conflicts.
The goal is to compute the set of all valid schedules given an input list of courses.
A model of constraints is initially constructed for a boolean SAT solver to determine if the set of valid schedules is non-empty.
For the input list, the size of possible schedules is calculated to determine if an exhaustive search of valid schedules is computationally feasible.
If such a search is expected to be too expensive, one of two strategies is employed to maximally explore the search space of schedules.
Strategy 1: a number of random schedules are sampled from the domain of all schedules.
All of the sampled schedules are assessed for validity.
Strategy 2: the previously constructed boolean SAT model is reused to compute solutions.
The latter strategy carries overhead due to boolean mapping, but is far more powerful than strategy 1 when the number of time conflicts is high.
After collecting a subset of valid schedules, all schedules are ranked against each other on 3 heuristics:

- Time variance across days: classes should start at roughly the same time every day, and, less importantly, end at the same time.
- Time spent in class: there should not be large time gaps in-between classes.
- Favourable breaks: for every *k* consecutive hours spent in class, a break is favourable to have.

The weightage of each factor can be adjusted to accommodate for user preference to produce a sorted ranking of all valid schedules.
This ranking strategy results in each schedule having a numerical score relative to every other schedule.
To eliminate poor schedules, a cutoff rank discards all schedules below it.
