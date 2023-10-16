# schedubuddy-server

This program is the server back-end of [schedubuddy](https://schedubuddy.com/), a schedule generator for the [University of Alberta](https://www.ualberta.ca/index.html).
This codebase handles the construction of a local database which it then uses itself.
Raw data is processed to generate several schedules for a queried list of courses, and then ranked and filtered according to user preferences.
This is useful for when a student knows the courses they wish to take, and wants to create an optimal schedule.

## How to update

Run `scrape.py` in the [util]() folder.
The Catalogue site changes the HTML occasionally,
and usually this is the file that will need correcting if that's the case.
This will scrape all the courses listed on the catalogue,
and generate a `raw.json` which contains characterizing information for each course instance. Afterward, run `make_local_db.py` to create the SQLite DB the backend queries.


You can then run the flask app and check that classes were added, updated (prof info), or removed.
We only track current and future terms.

## API

TODO. For now, the endpoints are available in app.py. Feel free to use the deployed Schedubuddy API at `https://schedubuddy1.herokuapp.com//api/v1/` for your own projects.

## Schedule generation

TODO
