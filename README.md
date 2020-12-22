# fis_check

## functionality

### basic: check results

- [x] cache calendar / form options
- [x] parse calendar from html to event level dict
  - [x] pull calendar filtered with sectorcode=AL, categorycode=WC, seasoncode=2021
  - [ ] use an object rather than dict
- [ ] parse event page into dict/object
- [ ] parse result page into dict/object
- [ ] create summary from result object
  - [ ] bin bibs by 10 (0: 1-10, 1: 11-20, 2: 21-30, ...)
  - [ ] what is the maximum value of the highest bin in the top 5
  - [ ] bin size as param
  - [ ] top X as param
- [ ] display the summaries of events based on filter criteria
  - [ ] sectorcode=AL
  - [ ] categorycode=WC
  - [ ] seasoncode=2021
  - [ ] date range: 2w window
  - [ ] discplinecode in (SG, DH)
- [ ] Allow filter options as parameters
- [ ] Adjust summary for multi-run disciplines (SL, GS)
- [ ] Store calendar / results locally so don't need to keep scraping constantly
  - [ ] Poll calendar in background for new events / results (daily? weekly?)
  - [ ] Check for results automatically based on local event calendar

### maybe?

- add some country info to summaries? did country X have anyone in top Y, etc.
- process non-alpine race results
- analysis / visualization of top X racers by split times / speeds in results
  - LIVE analysis / visualization of ...
