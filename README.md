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
    ...
  ]
}
```

## Schedule generation

To be documented in the future.
