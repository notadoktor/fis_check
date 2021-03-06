# fis_check

## functionality

### basic: check results

- [x] cache calendar / form options
- [x] parse calendar from html to event level dict
  - [x] pull calendar filtered with sectorcode=AL, categorycode=WC, seasoncode=2021
  - [x] use an object rather than dict
- [x] parse event page into dict/object
- [x] parse result page into dict/object
- [x] create summary from result object
  - [x] bin bibs by 10 (0: 1-10, 1: 11-20, 2: 21-30, ...)
  - [x] what is the maximum value of the highest bin in the top 5
  - [x] top X as param
- [x] display the summaries of events based on filter criteria
  - [x] sectorcode=AL
  - [x] categorycode=WC
  - [x] seasoncode=2021
  - [x] date range: ~2w window~ 7d (default) window
  - [x] discplinecode in (SG, DH)
- [x] Allow filter options as parameters
- [ ] Adjust summary for multi-run disciplines (SL, GS)
- [x] Store calendar / results locally so don't need to keep scraping constantly
  - [ ] Poll calendar in background for new events / results (daily? weekly?)
  - [ ] Check for results automatically based on local event calendar
- [ ] also run as persistent REST service
  - [ ] basic front end UI for api

### maybe?

- add some country info to summaries? did country X have anyone in top Y, etc.
- process non-alpine race results
- analysis / visualization of top X racers by split times / speeds in results
  - LIVE analysis / visualization of ...
