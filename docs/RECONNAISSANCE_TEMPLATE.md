# Reconnaissance – Target Repository (Manual Day-One Analysis)

*Copy this into the interim PDF report and fill it for your chosen target codebase (e.g. this repo, jaffle_shop, or another).*

**Target:** ___________________________________________

**Date:** ___________________________________________

---

## 1. Primary Data Ingestion

Where does data first enter the system? Which source tables, APIs, or files?

*(Fill after running Cartographer and inspecting lineage roots.)*

---

## 2. Critical Outputs

List 3–5 most important output datasets, tables, or endpoints.

*(Use lineage graph sinks and out-degree as a guide.)*

---

## 3. Blast Radius

If the most critical module or table failed, what would be affected? How many downstream datasets or services?

*(Use Hydrologist blast_radius / descendants.)*

---

## 4. Business Logic

Where is core business logic concentrated vs. distributed? Which modules have the most functions/classes/imports?

*(Use Surveyor module graph and Day-One “business logic” answer.)*

---

## 5. Most Active Files (last 90 days)

Which files change most frequently? (Git velocity.)

*(Use Surveyor change_velocity_30d or metadata recent_commit_count.)*

---

*This template aligns with the Five FDE Day-One Questions from the challenge.*
