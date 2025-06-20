export const generateReportContent = (dashboardData, analysisId) => {
  const {
    compatibility_score,
    skill_alignment,
    student_intents,
    counseling_report,
    input_data,
    company_culture,
    analysis_summary,
    status
  } = dashboardData;

  return `
CAREER COMPATIBILITY ANALYSIS REPORT
Generated on: ${new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })}

═══════════════════════════════════════════════════════════════════════════════

EXECUTIVE SUMMARY
═══════════════════════════════════════════════════════════════════════════════

Overall Compatibility Score: ${compatibility_score.overall_score}%

This report provides a comprehensive analysis of your career compatibility with the target company/role. The analysis evaluates your skills, career goals, and cultural preferences against the company's requirements and culture.

KEY METRICS:
• Overall Score: ${compatibility_score.overall_score}%
• Intent Alignment: ${compatibility_score.intent_alignment}%
• Skill Match: ${compatibility_score.skill_match}%
• Cultural Fit: ${compatibility_score.cultural_fit}%
• Confidence Level: ${compatibility_score.metadata?.confidence || 'N/A'}

═══════════════════════════════════════════════════════════════════════════════

YOUR CAREER PROFILE
═══════════════════════════════════════════════════════════════════════════════

CAREER GOALS:
${input_data?.career_goals || 'No specific career goals provided.'}

DESIRED INDUSTRIES:
${student_intents.desired_industries.map(industry => `• ${industry}`).join('\n')}

PREFERRED WORK CULTURE:
${student_intents.preferred_culture.map(culture => `• ${culture}`).join('\n')}

WORK PREFERENCES:
${student_intents.work_preferences.map(pref => `• ${pref}`).join('\n')}

LEARNING GOALS:
${student_intents.learning_goals.map(goal => `• ${goal}`).join('\n')}

CAREER ASPIRATIONS:
${student_intents.career_aspirations.map(aspiration => `• ${aspiration}`).join('\n')}

═══════════════════════════════════════════════════════════════════════════════

SKILL ANALYSIS
═══════════════════════════════════════════════════════════════════════════════

MATCHED SKILLS (${skill_alignment.matched_skills.length} skills):
${skill_alignment.matched_skills.map(skill => `✓ ${skill}`).join('\n')}

SKILL GAPS:
${skill_alignment.skill_gaps.length === 0 ?
    '• No specific skill gaps identified' :
    skill_alignment.skill_gaps.map(gap => `• ${gap}`).join('\n')}

TRANSFERABLE SKILLS:
${skill_alignment.transferable_skills.map(skill => `• ${skill}`).join('\n')}

HIDDEN OPPORTUNITIES:
${skill_alignment.hidden_opportunities.map(opportunity => `• ${opportunity}`).join('\n')}

═══════════════════════════════════════════════════════════════════════════════

COMPANY CULTURE MATCH
═══════════════════════════════════════════════════════════════════════════════

COMPANY VALUES:
${company_culture.values.map(value => `• ${value}`).join('\n')}

WORK-LIFE BALANCE:
${company_culture.work_life_balance}

LEARNING SUPPORT:
${company_culture.learning_support.map(support => `• ${support}`).join('\n')}

TEAM CULTURE:
${company_culture.team_culture}

COMPANY SIZE: ${company_culture.company_size}

═══════════════════════════════════════════════════════════════════════════════

COMPATIBILITY ASSESSMENT
═══════════════════════════════════════════════════════════════════════════════

MATCH REASONING:
${counseling_report.match_reasoning}

ANALYSIS SUMMARY:
${analysis_summary}

═══════════════════════════════════════════════════════════════════════════════

RECOMMENDATIONS & ACTION PLAN
═══════════════════════════════════════════════════════════════════════════════

IMMEDIATE ACTIONS:
${counseling_report.actionable_advice.map((advice, index) => `${index + 1}. ${advice}`).join('\n\n')}

ALTERNATIVE CAREER PATHS:
${counseling_report.alternative_suggestions.map((suggestion, index) => `${index + 1}. ${suggestion}`).join('\n\n')}

SKILL DEVELOPMENT ROADMAP:
${counseling_report.skill_development_plan.map((plan, index) => `${index + 1}. ${plan}`).join('\n\n')}

═══════════════════════════════════════════════════════════════════════════════

NEXT STEPS
═══════════════════════════════════════════════════════════════════════════════

1. IMMEDIATE ACTIONS (Next 1–2 weeks):
   • Review the skill gaps and prioritize the most critical ones
   • Start researching learning resources for your identified learning goals
   • Begin networking with professionals in your target industries

2. SHORT-TERM GOALS (Next 1–3 months):
   • Enroll in courses or bootcamps for your priority skills
   • Start building projects to demonstrate your capabilities
   • Update your resume and LinkedIn profile with new skills

3. MEDIUM-TERM GOALS (Next 3–6 months):
   • Complete significant projects showcasing your improved skills
   • Apply for internships or entry-level positions
   • Seek mentorship from industry professionals

4. LONG-TERM GOALS (Next 6–12 months):
   • Target roles that align with your compatibility scores
   • Continue building your professional network
   • Regularly reassess and update your career goals

═══════════════════════════════════════════════════════════════════════════════

REPORT METADATA
═══════════════════════════════════════════════════════════════════════════════

Analysis ID: ${analysisId}
Generated: ${new Date().toISOString()}
Analysis Version: ${compatibility_score.metadata?.analysis_version || '1.0'}
Report Status: ${status || 'Completed'}

═══════════════════════════════════════════════════════════════════════════════

This report is generated automatically based on your inputs and company data.
For personalized career counseling, consider consulting with a career advisor.

End of Report
  `.trim();
};
