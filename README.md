# schedubuddy-server

This program is the server back-end of [schedubuddy](https://schedubuddy.com/), a schedule generator for the [University of Alberta](https://www.ualberta.ca/index.html).
This program queries a local database that is constructed and updated by utility functions in the util folder of this repository.
Raw data is then processed to generate several schedules for a queried list of courses, and then ranked/filtered by various user-provided metrics.
This is useful for when a student knows the courses they wish to take, and wants to create an optimal schedule.

The remainder of this document will explain the API and discuss the schedule generation process.

## API

### Objects
There are three important objects that every endpoint is concerned with.
Term objects describe an academic term by name, dates, and the term ID.
The API will return all terms in the local database, however, when the database is being constructed/updated, it will only fetch ongoing or future terms.
The course object describes a course with various useful attributes (see examples).
Note that this object does not include class times because a course by itself is distinct from a class.
The class object is that which contains class time, instructor, location, and other class-specific information.

#### Term object example
```yaml
{
  "endDate": "2021-12-07", 
  "startDate": "2021-09-01", 
  "term": "1770", 
  "termTitle": "Fall Term 2021"
}
```

#### Course object example
```yaml
{
  "asString": "MATH 125", 
  "career": "UGRD", 
  "catalog": "125", 
  "course": "011487", 
  "courseDescription": "Systems of linear equations. Vectors in n-space, vector ...", 
  "courseTitle": "Linear Algebra I", 
  "department": "Department of Mathematical and Statistical Sciences", 
  "departmentCode": "MATH SCI", 
  "faculty": "Faculty of Science", 
  "facultyCode": "SC", 
  "subject": "MATH", 
  "subjectTitle": "Mathematics", 
  "term": "1770", 
  "units": "3.00"
} 
```

#### Class object example
```yaml
{
  "asString": "MATH 125 LEC A1", 
  "autoEnroll": null, 
  "campus": "MAIN", 
  "capacity": "160", 
  "class": "50354", 
  "classNotes": "Students in bridging programs can begin registering on Sept 7.", 
  "classStatus": "A", 
  "classType": "E", 
  "classtimes": [
    {
      "day": "MWF", 
      "endDate": "2021-12-07", 
      "endTime": "09:50 AM", 
      "location": "CCIS L1-140", 
      "startDate": "2021-09-01", 
      "startTime": "09:00 AM"
    }
  ], 
  "component": "LEC", 
  "consent": "No Consent", 
  "course": "011487", 
  "endDate": "2021-12-07", 
  "enrollStatus": "C", 
  "examDate": "2021-12-15", 
  "examEndTime": "12:00 PM", 
  "examStartTime": "09:00 AM", 
  "examStatus": "Tentative", 
  "gradingBasis": "Graded", 
  "instructionMode": "In Person", 
  "instructorName": "Nicolas Guay", 
  "instructorUid": "nguay", 
  "location": "MAIN", 
  "section": "A1", 
  "session": "Regular Academic Session", 
  "startDate": "2021-09-01", 
  "term": "1770", 
  "units": "3.00"
}
```

### Endpoints

There are three endpoints that the current version of [schedubuddy](https://schedubuddy.com/) uses.
Upon loading the website, term data is requested to allow the user to select a term in which to use schedubuddy for.
When a term is selected, all the courses available for that course are requested so the user can select their course list.

**GET** `/api/v1/terms`

Response:
```yaml
{
  "objects": [
    <term object 1>,
    <term object 2>,
    ...,
    <term object n>
  ]
}
```

---

**GET** `/api/v1/courses/`

**Query Parameters**\
`term`: Term ID (e.g. 1770) to get courses for

Response:

```yaml
{
  "objects": [
    <course object 1>,
    <course object 2>,
    ...,
    <course object n>
  ]
}
```

Example: `/api/v1/courses/?term=1770`

---

**GET** `/api/v1/gen-schedules/`

**Query Parameters**\
`term`: Term ID (e.g. 1770) to get courses for\
`courses`: Array of course IDs\
`prefs`: Array indicating the desired preferences for schedule ranking.

The preferences array takes the following form:\
index `0`: Evening classes considered (1) or not (0)\
index `1`: Online classes considered (1) or not (0)\
index `2`: Preferred start time for classes, e.g. `10:00 AM`\
index `3`: Preferred hours of class before a break, e.g. `2`\
index `4`: Number of schedules to display, e.g. `30`

Response:

```yaml
{
  "objects": {
    "aliases": {
      alias_key_1: [
        [
          <class id>,
          <class component>
        ],
        <alias tuple 2>,
        ...,
        <alias tuple n>
      ]
      <alias 2>,
      ...,
      <alias n>
    }
    "schedules": [
      [
        <class object>,
        <class object>,
        ...,
        <class object>
      ],
      <schedule array 2>,
      ...,
      <schedule array n>
    ]
  }
}
```

Example: `/api/v1/gen-schedules/?term=1770&courses=[011487,106431,096650]&prefs=[1,1,10:00%20AM,2,30]`

*Please note that the way that aliasing information is provided will be changed in the future.*

___

## Schedule generation

TBD
