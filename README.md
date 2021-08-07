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

TBD
