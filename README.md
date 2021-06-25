# schedubuddy-server

This program is the server implementation of a schedule generator for the [University of Alberta](https://www.ualberta.ca/index.html).
Given a list of courses, several schedules will be generated and ordered by various metrics. More info to be added in the future.

Start the server with: `python3 app.py`

## API
GET `/api/v1/terms`
```yaml
{
  "objects": [
    {
      "endDate": "2021-06-16", 
      "startDate": "2021-05-03", 
      "term": "1750", 
      "termTitle": "Spring Term 2021"
    },
    {<term object 2>},
    ...,
    {<term object n>}
  ]
}
```
GET `/api/v1/courses/?term=1770`

```yaml
{
  "objects": [
    {
      "asString": "CMPUT 404", 
      "career": "UGRD", 
      "catalog": "404", 
      "course": "106082",
      <course attribute 5>,
      ...,
      <course attribute n>
    },
    {<course object 2>},
    ...,
    {<course object n>}
  ]
}
```

GET `/api/v1/departments/?term=1770&code=COMPUT SCI`
```yaml
{
  "objects": [
    {<course object 1>},
    {<course object 2>},
    ...,
    {<course object n>}
  ]
}
```

GET `/api/v1/classes/?term=1770&course=096650`
```yaml
{
  "objects": [
    {
      "asString": "MATH 117 LEC SA1",
      ...
      <class attributes>,
      ...
      "classtimes": [
        {
          "day": "R", 
          "endDate": "2021-12-07", 
          "endTime": "01:50 PM", 
          "startDate": "2021-09-01", 
          "startTime": "01:00 PM"
        },
        {<classtime object 2>}
      ], 
      "component": "LEC",
      ...,
      <class attributes>,
      ...
    }, 
```

GET `api/v1/gen-schedules?term=1770&courses=[096650,006776,097174,010807,096909]`
```yaml
{
  "objects": [
    {<class object 1>},
    {<class object 2>},
    ...,
    {<class object n>}
  ]
}
```

## Schedule generation
A "valid" schedule is one that has no time conflicts. The goal is to compute the set of all valid schedules given an input list of courses.
A boolean SAT solver is initially provided constraints to determine if the set of valid schedules is non-empty.
For the input list, the size of possible schedules is calculated to determine if an exhaustive search of valid schedules is computationally feasible.
If such a search is expected to be too expensive, a number of random schedules are sampled from the domain of all schedules.
All of the sampled schedules are assessed for validity.
In practice, this usually results in numerous (>1000) valid schedules in a reasonable amount of time<sup>1</sup>.
All schedules in the resulting set are ranked against each other on 3 heuristics:
  - Time variance across days: classes should start at roughly the same time every day, and, less importantly, end at the same time.
  - Time spent in class: there should not be large gaps in-between classes. The user should instead block out busy times<sup>2</sup>.
  - Fvourable breaks: for every X consecutive hours spent in class, a break is favourable to have.
  
The weightage of each factor can be adjusted to accommodate for user preference to produce a sorted ranking of all valid schedules.
This strategy results in each schedule having a numerical score relative to every other schedule.
A fixed maximum number of top schedules are outputted to eliminate poor schedules.

###### <sup>1</sup> This process may be parallelizable, although this has not yet been investigated.<br></br><sup>2</sup> Blocking out times has not yet been implemented.

To be documented in the future.
