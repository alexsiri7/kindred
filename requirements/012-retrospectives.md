---
id: "012"
title: "Weekly/monthly retrospective reports"
status: "idea"
github_issue: 120
updated: "2026-05-12"
---

## Why

Individual entries capture moments, but users also need periodic summaries — what patterns dominated this week, what moods recurred, what shifted. Without retrospective reports, the longitudinal value of journaling stays invisible.

## What

Aggregated weekly and monthly reports generated from existing entries and pattern occurrences within a date range. Each report would include: entry count and mood distribution for the period, patterns that appeared (with frequency and average intensity), notable intensity spikes, and a narrative summary. Delivery via new backend endpoints (`GET /reports/weekly`, `GET /reports/monthly`) and a `/reports` web page with a date picker. Not yet built; the data model fully supports it once entries and patterns are flowing.
