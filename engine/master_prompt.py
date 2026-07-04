"""
Master Prompt Generator
Produces the prompt the user copies into ChatGPT/Claude
to get properly structured JSON output.
"""

MASTER_PROMPT = """
You are an expert resume transformation specialist. I will give you a job description. Your task is to completely transform my resume content so every single line sounds like it belongs to someone who has been doing exactly this role for years.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL — ROLE LANGUAGE RULE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Do NOT just add keywords. REFRAME everything.

If the role is Sales → everything sounds like sales. Even a web development project becomes: "pitched the platform concept to stakeholders", "identified customer pain points through user surveys", "drove adoption by communicating product value to target users", "negotiated feature priorities across teams".

If the role is Data Analyst → everything sounds analytical: "extracted insights from structured datasets", "built dashboards to track KPIs", "identified revenue patterns through cohort analysis".

If the role is HR → everything sounds people-focused: "assessed team dynamics and engagement levels", "structured onboarding workflows", "evaluated performance criteria".

Be creative, be bold, be believable. The projects are real — only the framing changes. A telemedicine project for a sales role should sound like you were selling healthcare solutions to rural communities.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL — ONE-PAGE LENGTH OPTIMIZATION RULE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. The output resume must fit on EXACTLY ONE PAGE. Be extremely concise.
2. If a project is not highly relevant to the target job description, set "include": false in the JSON to completely exclude it.
3. For the projects you include, limit bullets to 2 concise, high-impact items instead of 3 if the content is long or if it helps fit the document on one page. Bullet points must be short (max 1.5 lines each).
4. Shorten the "profile_summary" to 2 sentences max. Keep it dense and punchy.
5. If the job description is very specific, strip out any generic certifications or extracurriculars that don't add value to this role.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Output ONLY valid JSON. Zero text before or after it. No markdown. No explanation.
2. Project names are FIXED — never change: EcoAlchemy, InsightFlow, RuralCare.
3. Pick EXACTLY 4 certifications from the pool below. Choose the ones most relevant to this role. Copy name, provider, year EXACTLY as written in the pool.
4. Rewrite cert descriptions in one sentence to sound role-specific.
5. EXTRACURRICULARS — STRICT RULE: Return EXACTLY 3 extracurricular items in the JSON — no more, no fewer. Pick the 3 most relevant to the role from the 4 options below. Keep the activity name prefix exactly as written (e.g. "Smart India Hackathon —", "TEDx Volunteer —") and reframe the description in ONE concise sentence to sound role-relevant.
6. Everything must fit comfortably in ONE PAGE. Be concise. Bullet points max 1.5 lines each.
7. title_line format: "Role Title | Focus Area | Focus Area"
8. Set include: false for projects completely irrelevant to this role. Otherwise include: true.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CERTIFICATION POOL — Pick exactly 4:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  Machine Learning Terminology and Process | AWS Training & Certification | 2025
2.  Solutions Architecture Job Simulation | AWS — Forage | 2025
3.  Technology Software Development Job Simulation | Forage | 2025
4.  Software Engineering Job Simulation | Forage | 2025
5.  Introduction to Java Spring Framework 101 | Simplilearn SkillUp | 2025
6.  Software Engineering Job Simulation (Backend Integration) | Forage | 2025
7.  Advisors & Consulting Services Job Simulation | Forage | 2026
8.  Integrated Consulting Group Job Simulation | Forage | 2026
9.  Performance Appraisal Quiz Series — Quiz 2 | IIM Rohtak via Unstop | 2025
10. Management Consulting Simulation | Forage | 2026
11. Business Management & Innovation Studies | NPTEL — IIT Madras | 2025
12. Smart India Hackathon Participation | Fr. Conceicao Rodrigues College of Engineering | 2024
13. The Next Buffet Challenge — Stock Pitching | XLRI Delhi via Unstop | 2025
14. Supply Chain Strategies for Emerging Markets | DMS IIT Delhi / ISCEA | 2025
15. Data Visualisation: Empowering Business with Effective Insights | Tata — Forage | 2025
16. Cloud Architecture & Machine Learning Foundations | Amazon Web Services (AWS) | 2024-2025
17. Consulting & Strategy Simulations | PwC, Oliver Wyman, Mastercard — Forage | 2025-2026
18. Data Analysis & Business Insight Development | Tata — Forage | 2024-2025
19. AI in Human Resource Management | NPTEL — IIT Guwahati (SWAYAM) | 2026
20. Business Planning & Project Management | SWAYAM — Savitribai Phule Pune University | 2026
21. Data Analytics with Python | NPTEL — IIT Roorkee (SWAYAM) | 2026
22. Human Computer Interaction | NPTEL — IIT Madras / IIIT Delhi (SWAYAM) | 2026
23. Research Methodology | NPTEL — IIT Madras (SWAYAM) | 2025
24. Roadmap for Patent Creation | NPTEL — IIT Kharagpur (SWAYAM) | 2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JSON TEMPLATE — Fill every field:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{
  "title_line": "Role Title | Focus Area | Focus Area",
  "profile_summary": "2-3 sentences. Sound exactly like this role. Highlight relevant skills and impact. No first person.",
  "core_competencies": {
    "row1_label": "Category label for technical/domain skills",
    "row1_skills": ["Skill1", "Skill2", "Skill3", "Skill4", "Skill5"],
    "row2_label": "Category label for business/data/domain skills",
    "row2_skills": ["Skill1", "Skill2", "Skill3", "Skill4"],
    "row3_label": "Soft Skills",
    "row3_skills": ["Skill1", "Skill2", "Skill3", "Skill4"]
  },
  "certifications": [
    {
      "name": "Exact cert name from pool",
      "provider": "Exact provider from pool",
      "year": "Exact year from pool",
      "description": "One sentence reframed to sound relevant to this specific role."
    },
    {
      "name": "Exact cert name from pool",
      "provider": "Exact provider from pool",
      "year": "Exact year from pool",
      "description": "One sentence reframed to sound relevant to this specific role."
    },
    {
      "name": "Exact cert name from pool",
      "provider": "Exact provider from pool",
      "year": "Exact year from pool",
      "description": "One sentence reframed to sound relevant to this specific role."
    },
    {
      "name": "Exact cert name from pool",
      "provider": "Exact provider from pool",
      "year": "Exact year from pool",
      "description": "One sentence reframed to sound relevant to this specific role."
    }
  ],
  "projects": [
    {
      "name": "EcoAlchemy — Waste Exchange Platform",
      "year": "2024",
      "include": true,
      "bullets": [
        "Bullet 1 — rewritten to sound like this role. Be specific, use role keywords.",
        "Bullet 2 — rewritten to sound like this role.",
        "Bullet 3 — rewritten to sound like this role."
      ]
    },
    {
      "name": "InsightFlow — Customer Churn, Revenue Intelligence & Business Optimization Platform",
      "year": "2024",
      "include": true,
      "bullets": [
        "Bullet 1 — rewritten to sound like this role.",
        "Bullet 2 — rewritten to sound like this role.",
        "Bullet 3 — rewritten to sound like this role."
      ]
    },
    {
      "name": "RuralCare — Integrated Telemedicine & Treatment Management Platform",
      "year": "2024",
      "include": true,
      "bullets": [
        "Bullet 1 — rewritten to sound like this role.",
        "Bullet 2 — rewritten to sound like this role.",
        "Bullet 3 — rewritten to sound like this role."
      ]
    }
  ],
  "extracurriculars": [
    {
      "full_line": "[Keep exact prefix e.g. 'Smart India Hackathon —'] [1 sentence reframed for this role]"
    },
    {
      "full_line": "[Keep exact prefix e.g. 'TEDx Volunteer —'] [1 sentence reframed for this role]"
    },
    {
      "full_line": "[Keep exact prefix e.g. 'Rotaract Club Volunteer —'] [1 sentence reframed for this role]"
    }
  ]
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Job Description:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PASTE JOB DESCRIPTION HERE]
""".strip()


def get_master_prompt():
    return MASTER_PROMPT
