### Calendar

_URL_:

- `https://www.fis-ski.com/DB/general/calendar-results.html`
- `https://www.fis-ski.com/DB/$sectorcode/calendar-results.html`

```
div id=calendarloadcontainer class=section__body -> div class="table table_pb"
  div class=table__head -> div -> div -> div class="g-xs-24 container"
    div.string == column name
  div class=table__body -> div id=calendardata name="calendardata"
    # each child div is an event
    div id=$eventid -> div -> div class="g-row"
      <a> href: link to event page, a.string is
      div class="g-row" -> <a> children are info columns
        a[0] -> div class=status -> div -> div[0,1] -> span[0:1].title
        a[1] -> a.string: date
        a[2]
          div[0].string: location
          div[1].string: category (hidden)
          div[2].string: disciplines (hidden)
        a[3].string: location
        a[4]
          div[0].string: location
          div[1]: ?
        a[5] -> div -> div class="country country_flag"
          span[0] class=country__flag -> span class=flag-$country_code)
          span[1].string: $country_code
        a[6].string: sectorcode
        a[7] -> div
          div[0].string: category
          div[1].string: discipline(s)
        a[8]: hidden
        a[9] -> div -> div -> div.string: gendercode
        a[10] -> span -> svg (calendar icon)
```

URL: event_details

```
div class=section__content -> div class=section__body -> div class="table table_pb"
  div class=table__head -> div
    div[0] class="thead thead_striped" -> div
      div[0] -> div[].string: column title
      div[1] -> span -> svg (download icon)
    div[1] class="thead thead_slave hidden-xs" -> ... sub column headings
  div id=eventdetailscontent class=table__body
    # each child is 1 day/race
    div[] class="table-row" -> div class="container g-row"
      div[0] -> div class=g-row
        # each a href links to race results_
        a[0] -> div class=status -> div -> div[0,1] -> span[0:1].title
        a[1] -> div -> div -> div.string: date
        div[2] -> a href: details (short) -> div
          div[0] -> div.string: codex number
          div[1] -> div -> div.string: live status
        a[3] -> div -> div -> div -> div.string: discipline
        a[4]: hidden
        a[5].string: categorycode
        a[6] -> div -> div -> div.string: gendercode
        a[7] -> div -> div -> div class=g-row
          div[0].string: current run
          div[1].string: start time
          div[2].string: also start time?
          div[3].string: status
          div[4].string: info (?)
        a[8].string: comments
```

URL: event_results

```
div class=section__body -> div class=table
  div[0] class=table__head -> div -> div class="thead thead_striped" -> div -> div class=g-row
    div[].string: column title
  div[1] id=events-info-results -> div class=tbody
    # each child is column data
    a[0] -> div -> div
      div[0].string: rank
      div[1].string: bib
      div[2].string: FIS code
      div[3].string: LASTNAME firstname
      div[4].string: birth year
      div[5] -> div
        span[0] -> span class=flag-$country_code
        span[1].string: $country_code
      div[6].string: time
      div[7].string: difference from leader
```
