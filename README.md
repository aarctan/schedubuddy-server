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
  "courseDescription": "Systems of linear equations. Vectors in n-space, vector equations of ...", 
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

GET `/api/v1/terms`
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

GET `/api/v1/courses/`

TBD

GET `/api/v1/classes/`

TBD

GET `/api/v1/gen-schedules/`

TBD

## Schedule generation

TBD
