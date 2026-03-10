"""
Generate two architecture flowcharts for the OpenMRS Clinical Chatbot project.

Flowchart 1: OpenMRS Clinical Chatbot: An Intelligent Agent-Based Architecture
             for Pediatric Clinical Decision Support

Flowchart 2: OpenMRS-Integrated Chatbot for Pediatric Care: A Knowledge-Source
             Framework for Clinical Query Scenario Classification
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patheffects as pe

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ─────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ─────────────────────────────────────────────────────────────────────────────

def rounded_box(ax, x, y, width, height, text, facecolor, edgecolor='#333333',
                fontsize=9, text_color='white', bold=False, radius=0.015,
                linewidth=1.4, zorder=3, wrap_width=None):
    """Draw a rounded rectangle with centred text."""
    fancy = FancyBboxPatch(
        (x - width / 2, y - height / 2), width, height,
        boxstyle=f"round,pad={radius}",
        linewidth=linewidth, edgecolor=edgecolor,
        facecolor=facecolor, zorder=zorder
    )
    ax.add_patch(fancy)
    weight = 'bold' if bold else 'normal'
    ax.text(x, y, text, ha='center', va='center',
            fontsize=fontsize, color=text_color, weight=weight,
            zorder=zorder + 1,
            wrap=True,
            multialignment='center')


def diamond(ax, x, y, width, height, text, facecolor, edgecolor='#333333',
            fontsize=8.5, text_color='white', zorder=3):
    """Draw a diamond shape with centred text."""
    dx, dy = width / 2, height / 2
    xs = [x, x + dx, x, x - dx, x]
    ys = [y + dy, y, y - dy, y, y + dy]
    ax.fill(xs, ys, color=facecolor, zorder=zorder, linewidth=1.4,
            edgecolor=edgecolor)
    ax.text(x, y, text, ha='center', va='center',
            fontsize=fontsize, color=text_color, weight='bold',
            zorder=zorder + 1, multialignment='center')


def arrow(ax, x1, y1, x2, y2, color='#555555', lw=1.5, head=10, zorder=2):
    """Draw an annotated arrow between two points."""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=f'->', color=color,
                                lw=lw, mutation_scale=head),
                zorder=zorder)


def label_arrow(ax, x1, y1, x2, y2, label, color='#555555', lw=1.5,
                fontsize=7.5, zorder=2):
    """Draw an arrow with a small label at midpoint."""
    arrow(ax, x1, y1, x2, y2, color=color, lw=lw, zorder=zorder)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    ax.text(mx + 0.01, my, label, ha='left', va='center',
            fontsize=fontsize, color=color, style='italic', zorder=zorder + 1)


# ─────────────────────────────────────────────────────────────────────────────
# Colour palette
# ─────────────────────────────────────────────────────────────────────────────
C = {
    'user':       '#2E4057',  # dark navy  – user
    'triage':     '#048A81',  # teal       – triage / routing
    'agent':      '#1565C0',  # blue       – specialised agents
    'data':       '#6A1B9A',  # purple     – data layer
    'validation': '#B71C1C',  # dark red   – validation / safety
    'response':   '#1B5E20',  # dark green – response
    'output':     '#4E342E',  # brown      – output
    'ped':        '#E65100',  # deep orange – paediatric features
    'bg':         '#F5F5F5',
    'panel':      '#ECEFF1',
}


# ─────────────────────────────────────────────────────────────────────────────
# FLOWCHART 1 – Agent-Based Architecture
# ─────────────────────────────────────────────────────────────────────────────

def make_flowchart1():
    fig, ax = plt.subplots(figsize=(18, 26))
    fig.patch.set_facecolor(C['bg'])
    ax.set_facecolor(C['bg'])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # ── Title ────────────────────────────────────────────────────────────────
    ax.text(0.5, 0.975,
            'OpenMRS Clinical Chatbot:\nAn Intelligent Agent-Based Architecture\n'
            'for Pediatric Clinical Decision Support',
            ha='center', va='top', fontsize=15, weight='bold',
            color='#1A237E', multialignment='center')

    # ── Row y-coordinates (top → bottom) ────────────────────────────────────
    y_user   = 0.905
    y_triage = 0.820
    y_router = 0.745
    y_agents = 0.640   # row of specialised agent boxes
    y_data   = 0.495   # data layer boxes
    y_val    = 0.390
    y_resp   = 0.295
    y_out    = 0.195
    y_ped    = 0.090   # paediatric feature band

    BW  = 0.13   # box width
    BH  = 0.048  # box height (standard)
    BHT = 0.055  # box height (tall)

    # ── USER INPUT ───────────────────────────────────────────────────────────
    rounded_box(ax, 0.5, y_user, 0.30, BH,
                'USER INPUT\n(Doctor  |  Patient  |  Parent)',
                C['user'], bold=True, fontsize=10)

    # ── TRIAGE AGENT ────────────────────────────────────────────────────────
    rounded_box(ax, 0.5, y_triage, 0.46, BHT,
                'TRIAGE AGENT\n'
                '• Intent Classification (11 categories)\n'
                '• User Role Detection (Doctor / Patient)\n'
                '• Entity Extraction (Patient ID, Drug, Vaccine)',
                C['triage'], bold=False, fontsize=8.5)
    arrow(ax, 0.5, y_user - BH/2, 0.5, y_triage + BHT/2)

    # ── INTENT ROUTER ───────────────────────────────────────────────────────
    diamond(ax, 0.5, y_router, 0.28, 0.060,
            'INTENT ROUTER\n(Select Specialised Agent)',
            C['triage'])
    arrow(ax, 0.5, y_triage - BHT/2, 0.5, y_router + 0.030)

    # ── SPECIALISED AGENT BOXES ─────────────────────────────────────────────
    agents = [
        (0.09, 'MEDICATION\nAGENT\n• Dosage\n• Interactions\n• Administration'),
        (0.25, 'ALLERGY\nAGENT\n• Drug-Allergy\n  Checks\n• Contraindications'),
        (0.41, 'IMMUNIZATION\nAGENT\n• Vaccine History\n• Next Dose\n• Schedules'),
        (0.59, 'VITALS\nAGENT\n• SQL Queries\n• BMI Calc\n• Observations'),
        (0.75, 'PATIENT\nRECORD\nAGENT\n• Full Profile\n• Demographics'),
        (0.91, 'HYBRID\nAGENT\n• Multi-Intent\n• Combined\n  Queries'),
    ]
    agent_bh = 0.110
    for ax_x, txt in agents:
        rounded_box(ax, ax_x, y_agents, BW, agent_bh, txt,
                    C['agent'], fontsize=7.8)
        # arrow from diamond bottom to agent top
        # (approximate: diamond tip → agent box)
        ax.annotate('', xy=(ax_x, y_agents + agent_bh/2),
                    xytext=(0.5, y_router - 0.030),
                    arrowprops=dict(arrowstyle='->', color='#555555',
                                   lw=1.2, mutation_scale=8,
                                   connectionstyle='arc3,rad=0.0'),
                    zorder=2)

    # ── DATA RETRIEVAL LAYER ────────────────────────────────────────────────
    # panel background
    panel = FancyBboxPatch((0.03, y_data - 0.075), 0.94, 0.135,
                           boxstyle='round,pad=0.01',
                           linewidth=1.5, edgecolor='#9E9E9E',
                           facecolor=C['panel'], zorder=1)
    ax.add_patch(panel)
    ax.text(0.5, y_data + 0.055, 'DATA RETRIEVAL LAYER',
            ha='center', va='center', fontsize=9, weight='bold',
            color='#4A148C', zorder=4)

    data_sources = [
        (0.14, 'OpenMRS MySQL DB\n(patient, orders,\nobs, allergy,\nimmunization)'),
        (0.35, 'JSON Knowledge Bases\n(drug_knowledge_base,\nimmunization,\nmilestones)'),
        (0.57, 'ChromaDB\nVector Store\n(WHO Guidelines,\nCDC PDFs)'),
        (0.79, 'External APIs\n(RxNorm API\nFDA API)'),
    ]
    data_bh = 0.082
    for dx, txt in data_sources:
        rounded_box(ax, dx, y_data - 0.008, 0.18, data_bh, txt,
                    C['data'], fontsize=8)

    # arrows: each agent → data layer panel
    for ax_x, _ in agents:
        arrow(ax, ax_x, y_agents - agent_bh/2,
              ax_x, y_data + 0.065, lw=1.1, head=7)

    # ── VALIDATION AGENT ────────────────────────────────────────────────────
    rounded_box(ax, 0.5, y_val, 0.50, BHT,
                'VALIDATION AGENT  (Safety Layer)\n'
                '• Verify data existence  •  Prevent hallucinations\n'
                '• Check database connections  •  Validate patient IDs\n'
                '• Ensure no empty / unsafe responses',
                C['validation'], bold=False, fontsize=8.5)
    arrow(ax, 0.5, y_data - 0.075, 0.5, y_val + BHT/2)

    # ── RESPONSE AGENT ──────────────────────────────────────────────────────
    rounded_box(ax, 0.5, y_resp, 0.46, BHT,
                'RESPONSE AGENT  (Role-Based Formatting)\n'
                '• Doctor View: Clinical detail, drug IDs, safety alerts\n'
                '• Patient / Parent View: Simplified, plain language',
                C['response'], bold=False, fontsize=8.5)
    arrow(ax, 0.5, y_val - BHT/2, 0.5, y_resp + BHT/2)

    # ── OUTPUT ──────────────────────────────────────────────────────────────
    rounded_box(ax, 0.5, y_out, 0.34, BH,
                'OUTPUT\n(Formatted JSON  |  Audit Log  |  responses.json)',
                C['output'], bold=True, fontsize=9)
    arrow(ax, 0.5, y_resp - BHT/2, 0.5, y_out + BH/2)

    # ── PAEDIATRIC FEATURES BAND ────────────────────────────────────────────
    ped_panel = FancyBboxPatch((0.03, y_ped - 0.035), 0.94, 0.082,
                               boxstyle='round,pad=0.01',
                               linewidth=1.5, edgecolor='#BF360C',
                               facecolor='#FBE9E7', zorder=1)
    ax.add_patch(ped_panel)
    ax.text(0.5, y_ped + 0.030,
            'PAEDIATRIC CLINICAL DECISION SUPPORT FEATURES',
            ha='center', va='center', fontsize=9, weight='bold',
            color=C['ped'], zorder=4)
    ped_items = [
        '• Age-Based & Weight-Based\n  Drug Dosage Calculation',
        '• Immunization Schedule\n  Tracking & Next-Dose Prediction',
        '• Developmental Milestone\n  Assessment (CDC / WHO)',
        '• Drug–Allergy Safety Checks\n  & Contraindication Alerts',
        '• BMI Percentile Calculation\n  (Age-Adjusted for Children)',
    ]
    for i, txt in enumerate(ped_items):
        ax.text(0.09 + i * 0.185, y_ped - 0.004, txt,
                ha='center', va='center', fontsize=7.4,
                color='#BF360C', zorder=4, multialignment='center')

    # ── LEGEND ──────────────────────────────────────────────────────────────
    legend_x, legend_y = 0.71, 0.162
    legend_items = [
        (C['user'],       'User Interaction Layer'),
        (C['triage'],     'Triage & Routing'),
        (C['agent'],      'Specialised Agents'),
        (C['data'],       'Data Sources'),
        (C['validation'], 'Validation & Safety'),
        (C['response'],   'Response Generation'),
        (C['ped'],        'Paediatric Features'),
    ]
    ax.text(legend_x, legend_y + 0.008, 'LEGEND', fontsize=8,
            weight='bold', color='#333333', va='bottom')
    for i, (color, label) in enumerate(legend_items):
        ly = legend_y - 0.022 * (i + 1)
        rect = FancyBboxPatch((legend_x, ly - 0.007), 0.022, 0.014,
                              boxstyle='round,pad=0.002',
                              facecolor=color, edgecolor='#333333',
                              linewidth=0.8, zorder=5)
        ax.add_patch(rect)
        ax.text(legend_x + 0.028, ly, label,
                va='center', fontsize=7.5, color='#333333', zorder=5)

    plt.tight_layout(pad=0.3)
    out_path = os.path.join(OUTPUT_DIR, 'flowchart1_agent_architecture.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight',
                facecolor=C['bg'], edgecolor='none')
    plt.close(fig)
    print(f'Saved: {out_path}')


# ─────────────────────────────────────────────────────────────────────────────
# FLOWCHART 2 – Knowledge-Source / Query Classification Framework
# ─────────────────────────────────────────────────────────────────────────────

def make_flowchart2():
    fig, ax = plt.subplots(figsize=(20, 24))
    fig.patch.set_facecolor(C['bg'])
    ax.set_facecolor(C['bg'])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # ── Title ────────────────────────────────────────────────────────────────
    ax.text(0.5, 0.975,
            'OpenMRS-Integrated Chatbot for Pediatric Care:\n'
            'A Knowledge-Source Framework for\nClinical Query Scenario Classification',
            ha='center', va='top', fontsize=15, weight='bold',
            color='#1A237E', multialignment='center')

    # ── Colour overrides for this chart ─────────────────────────────────────
    COL = {
        'input':   '#2E4057',
        'triage':  '#00695C',
        'class':   '#1565C0',
        'omrs':    '#6A1B9A',
        'json':    '#00838F',
        'chroma':  '#4527A0',
        'api':     '#558B2F',
        'header':  '#37474F',
        'arrow':   '#546E7A',
        'panel_omrs':   '#F3E5F5',
        'panel_json':   '#E0F7FA',
        'panel_chroma': '#EDE7F6',
        'panel_api':    '#F1F8E9',
    }

    # ─── Row y-positions ────────────────────────────────────────────────────
    y_title_bar  = 0.906
    y_input      = 0.848
    y_triage     = 0.775
    y_classifier = 0.700

    # 11 query scenarios arranged in two columns
    scenario_top_y  = 0.630
    scenario_row_h  = 0.054
    n_scenarios     = 11
    col_xs          = [0.25, 0.75]   # left / right column x centres
    scenario_w      = 0.43
    scenario_h      = 0.042

    # Knowledge-source panels below scenarios
    ks_top_y    = 0.010
    ks_panel_h  = 0.270
    ks_top      = ks_top_y + ks_panel_h   # y of panel top edge

    # ── Section header band ──────────────────────────────────────────────────
    hdr = FancyBboxPatch((0.0, y_title_bar - 0.012), 1.0, 0.024,
                         boxstyle='square,pad=0',
                         facecolor='#1A237E', edgecolor='none', zorder=1)
    ax.add_patch(hdr)
    ax.text(0.5, y_title_bar, 'KNOWLEDGE-SOURCE FRAMEWORK  ×  CLINICAL QUERY CLASSIFICATION',
            ha='center', va='center', fontsize=9.5, color='white',
            weight='bold', zorder=2)

    # ── USER INPUT ───────────────────────────────────────────────────────────
    rounded_box(ax, 0.5, y_input, 0.30, 0.044,
                'CLINICAL QUERY  (Natural Language Input)',
                COL['input'], bold=True, fontsize=10)

    # ── TRIAGE AGENT ────────────────────────────────────────────────────────
    rounded_box(ax, 0.5, y_triage, 0.50, 0.050,
                'TRIAGE AGENT\n'
                'Keyword Matching  •  LLM (Ollama/llama2)  •  Confidence Scoring',
                COL['triage'], fontsize=9)
    arrow(ax, 0.5, y_input - 0.022, 0.5, y_triage + 0.025,
          color=COL['arrow'])

    # ── INTENT CLASSIFIER label ──────────────────────────────────────────────
    rounded_box(ax, 0.5, y_classifier, 0.36, 0.040,
                'CLINICAL QUERY SCENARIO CLASSIFIER\n'
                '(Returns: intent, user_role, patient_id, confidence)',
                COL['class'], fontsize=8.5)
    arrow(ax, 0.5, y_triage - 0.025, 0.5, y_classifier + 0.020,
          color=COL['arrow'])

    # ── QUERY SCENARIOS ──────────────────────────────────────────────────────
    scenarios = [
        # (label, description, mapped knowledge sources colour)
        ('MEDICATION_QUERY',
         'Drug dosage, side effects, dosing frequency',
         '#1565C0'),
        ('MEDICATION_INFO_QUERY',
         'Current prescribed medications for patient',
         '#1565C0'),
        ('MEDICATION_ADMINISTRATION_QUERY',
         'How to administer / give a medication',
         '#1565C0'),
        ('MEDICATION_SIDE_EFFECTS_QUERY',
         'Adverse effects, toxicity, reactions',
         '#1565C0'),
        ('MEDICATION_EMERGENCY_QUERY',
         'Overdose, missed dose — HIGH PRIORITY',
         '#C62828'),
        ('MEDICATION_COMPATIBILITY_QUERY',
         'Drug–drug interactions, simultaneous use',
         '#1565C0'),
        ('ALLERGY_QUERY',
         'Drug-allergy contraindication checks',
         '#6A1B9A'),
        ('IMMUNIZATION_QUERY',
         'Vaccination history, next dose, schedules',
         '#00838F'),
        ('VITALS_QUERY',
         'Vital signs, BMI, weight, height, BP',
         '#4527A0'),
        ('PATIENT_RECORD_QUERY',
         'Full demographic & clinical profile',
         '#37474F'),
        ('HYBRID_QUERY',
         'Multi-intent — combined knowledge sources',
         '#E65100'),
    ]

    # Draw two-column grid of scenarios
    ax.text(0.5, scenario_top_y + 0.025,
            'QUERY SCENARIO CATEGORIES',
            ha='center', va='center', fontsize=9, weight='bold',
            color=C['triage'])
    arrow(ax, 0.5, y_classifier - 0.020, 0.5, scenario_top_y + 0.013,
          color=COL['arrow'])

    for i, (intent, desc, color) in enumerate(scenarios):
        col  = i % 2          # 0 = left, 1 = right
        row  = i // 2
        sx   = col_xs[col]
        sy   = scenario_top_y - 0.014 - row * scenario_row_h
        txt  = f'{intent}\n{desc}'
        rounded_box(ax, sx, sy, scenario_w, scenario_h, txt,
                    color, fontsize=7.8, radius=0.010)

    # ── KNOWLEDGE SOURCE PANELS ──────────────────────────────────────────────
    ks_panel_y_bottom = ks_top_y
    ks_panel_top = ks_top_y + ks_panel_h

    # Section header
    ax.text(0.5, ks_panel_top + 0.012,
            'KNOWLEDGE SOURCES',
            ha='center', va='center', fontsize=10, weight='bold',
            color='#1A237E')

    # Draw four KS panels side by side
    panel_w  = 0.215
    panel_xs = [0.110, 0.335, 0.560, 0.785]
    panel_h  = 0.235

    # ── OpenMRS MySQL DB ────────────────────────────────────────────────────
    p1 = FancyBboxPatch((panel_xs[0] - panel_w/2, ks_panel_y_bottom),
                        panel_w, panel_h,
                        boxstyle='round,pad=0.008',
                        facecolor=COL['panel_omrs'], edgecolor=COL['omrs'],
                        linewidth=1.8, zorder=2)
    ax.add_patch(p1)
    ax.text(panel_xs[0], ks_panel_y_bottom + panel_h - 0.018,
            'OpenMRS MySQL DB', ha='center', va='top',
            fontsize=9, weight='bold', color=COL['omrs'], zorder=3)
    omrs_lines = [
        'patient  – demographics',
        'person   – DOB, gender',
        'orders   – active medications',
        'obs      – vitals (weight, BP…)',
        'allergy  – allergies + severity',
        'immunization – vaccine history',
        '',
        'Queries: MEDICATION_INFO,',
        'ALLERGY, IMMUNIZATION,',
        'VITALS, PATIENT_RECORD,',
        'HYBRID',
    ]
    ax.text(panel_xs[0], ks_panel_y_bottom + panel_h - 0.036,
            '\n'.join(omrs_lines),
            ha='center', va='top', fontsize=7.2,
            color='#4A148C', zorder=3, multialignment='center',
            linespacing=1.4)

    # ── JSON Knowledge Bases ────────────────────────────────────────────────
    p2 = FancyBboxPatch((panel_xs[1] - panel_w/2, ks_panel_y_bottom),
                        panel_w, panel_h,
                        boxstyle='round,pad=0.008',
                        facecolor=COL['panel_json'], edgecolor=COL['json'],
                        linewidth=1.8, zorder=2)
    ax.add_patch(p2)
    ax.text(panel_xs[1], ks_panel_y_bottom + panel_h - 0.018,
            'JSON Knowledge Bases', ha='center', va='top',
            fontsize=9, weight='bold', color=COL['json'], zorder=3)
    json_lines = [
        'drug_knowledge_base.json',
        '  • Indications & dosing',
        '  • Contraindications',
        '  • Paediatric mg/kg doses',
        '  • Drug interactions',
        '',
        'immunization.json',
        '  • Vaccine schedules',
        '  • Dose intervals',
        '',
        'milestones.json',
        '  • Developmental milestones',
        '',
        'Queries: MEDICATION_*,',
        'IMMUNIZATION, HYBRID',
    ]
    ax.text(panel_xs[1], ks_panel_y_bottom + panel_h - 0.036,
            '\n'.join(json_lines),
            ha='center', va='top', fontsize=7.0,
            color='#006064', zorder=3, multialignment='center',
            linespacing=1.35)

    # ── ChromaDB Vector Store ────────────────────────────────────────────────
    p3 = FancyBboxPatch((panel_xs[2] - panel_w/2, ks_panel_y_bottom),
                        panel_w, panel_h,
                        boxstyle='round,pad=0.008',
                        facecolor=COL['panel_chroma'], edgecolor=COL['chroma'],
                        linewidth=1.8, zorder=2)
    ax.add_patch(p3)
    ax.text(panel_xs[2], ks_panel_y_bottom + panel_h - 0.018,
            'ChromaDB Vector Store', ha='center', va='top',
            fontsize=9, weight='bold', color=COL['chroma'], zorder=3)
    chroma_lines = [
        'Indexed PDF documents',
        '(Semantic RAG retrieval)',
        '',
        'Doctor KB:',
        '  • WHO Essential Medicines',
        '    2023 List (PDF)',
        '  • CDC Milestone Checklists',
        '',
        'Patient KB:',
        '  • CDC Milestone Checklists',
        '    (parent-friendly)',
        '',
        'Queries: MEDICATION_QUERY,',
        'MEDICATION_EMERGENCY,',
        'HYBRID',
    ]
    ax.text(panel_xs[2], ks_panel_y_bottom + panel_h - 0.036,
            '\n'.join(chroma_lines),
            ha='center', va='top', fontsize=7.0,
            color='#311B92', zorder=3, multialignment='center',
            linespacing=1.35)

    # ── External APIs ────────────────────────────────────────────────────────
    p4 = FancyBboxPatch((panel_xs[3] - panel_w/2, ks_panel_y_bottom),
                        panel_w, panel_h,
                        boxstyle='round,pad=0.008',
                        facecolor=COL['panel_api'], edgecolor=COL['api'],
                        linewidth=1.8, zorder=2)
    ax.add_patch(p4)
    ax.text(panel_xs[3], ks_panel_y_bottom + panel_h - 0.018,
            'External APIs', ha='center', va='top',
            fontsize=9, weight='bold', color=COL['api'], zorder=3)
    api_lines = [
        'RxNorm API',
        '  • Drug name normalisation',
        '  • Drug concept IDs',
        '  • Interaction data',
        '',
        'FDA API',
        '  • Drug labelling data',
        '  • Adverse event reports',
        '  • Drug recalls',
        '',
        'Queries:',
        'MEDICATION_COMPATIBILITY,',
        'MEDICATION_EMERGENCY,',
        'HYBRID',
    ]
    ax.text(panel_xs[3], ks_panel_y_bottom + panel_h - 0.036,
            '\n'.join(api_lines),
            ha='center', va='top', fontsize=7.0,
            color='#33691E', zorder=3, multialignment='center',
            linespacing=1.35)

    # ── Arrows from scenario grid to KS panels ───────────────────────────────
    # Bottom of scenario grid → top of KS panels
    scenario_bottom_y = scenario_top_y - 0.014 - (n_scenarios // 2) * scenario_row_h - scenario_h / 2
    ks_panel_top_y = ks_panel_y_bottom + panel_h

    mapping_y = (scenario_bottom_y + ks_panel_top_y) / 2

    ax.text(0.5, mapping_y + 0.012,
            '▼  Each query scenario is mapped to its primary knowledge source(s)  ▼',
            ha='center', va='center', fontsize=8.5, style='italic',
            color='#37474F')

    for px in panel_xs:
        arrow(ax, px, ks_panel_top_y,
              px, scenario_bottom_y + 0.008,
              color=COL['arrow'], lw=1.5, head=9)

    plt.tight_layout(pad=0.3)
    out_path = os.path.join(OUTPUT_DIR, 'flowchart2_knowledge_classification.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight',
                facecolor=C['bg'], edgecolor='none')
    plt.close(fig)
    print(f'Saved: {out_path}')


# ─────────────────────────────────────────────────────────────────────────────
# FLOWCHART 3 – Architecture, Flow, and Safety Logic  (horizontal 7-module view)
#
# This is a fixed/polished version of the "Architecture, Flow, and Safety Logic"
# diagram.  Bugs corrected vs. the reference image:
#   1. All connecting arrows are drawn (modules 4→5, 5→6, 6→7, and every
#      query-type box → module 4).
#   2. The "4. Data Retrieval Layer" title is placed INSIDE its container box
#      (the reference had it floating below the box).
#   3. Uniform styling throughout: identical header treatment, consistent box
#      borders, font sizes, and arrow weights for every module.
# ─────────────────────────────────────────────────────────────────────────────

def make_flowchart3():
    """Horizontal 7-module architecture diagram with all arrows & uniform style."""

    WHITE = '#FFFFFF'
    NAVY  = '#1A237E'
    BLUE  = '#1565C0'
    BLU_F = '#EBF5FB'   # very-light blue fill used by all modules
    ARROW = '#1565C0'

    # Query box (fill, edge) colour pairs – six distinct pastel tones
    Q_COL = [
        ('#AED6F1', '#1565C0'),  # Medication Query      – sky blue
        ('#FAD7A0', '#E67E22'),  # Allergy Query         – peach
        ('#A9DFBF', '#27AE60'),  # Immunization Query    – green
        ('#D2B4DE', '#7D3C98'),  # Vitals Query          – lavender
        ('#FADBD8', '#CB4335'),  # Patient Record Query  – salmon
        ('#A3E4D7', '#17A589'),  # Hybrid Query          – teal
    ]

    # ── Figure ───────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(28, 16))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # ── Column layout (centre x, half-width) ────────────────────────────────
    # 7 module columns + 6 inter-column gaps of 0.024
    # Gap between Triage and Query boxes holds the "3. Intent Routing" label
    GAP = 0.024
    M1cx, M1hw = 0.078, 0.049   # 1. User Input
    M2cx, M2hw = 0.211, 0.062   # 2. Triage Agent
    QXcx, QXhw = 0.358, 0.054   # 3. Query-type boxes
    M4cx, M4hw = 0.504, 0.062   # 4. Data Retrieval Layer (container)
    M5cx, M5hw = 0.638, 0.054   # 5. Validation Agent
    M6cx, M6hw = 0.775, 0.058   # 6. Response Agent
    M7cx, M7hw = 0.909, 0.050   # 7. User Output

    # Vertical module extents (every module shares the same top / bottom)
    MOD_TOP = 0.905
    MOD_BOT = 0.090
    MOD_H   = MOD_TOP - MOD_BOT          # 0.815
    MOD_CEN = (MOD_TOP + MOD_BOT) / 2    # 0.4975

    # Query-box stack (6 boxes centred vertically inside [MOD_BOT, MOD_TOP])
    N_Q   = 6
    Q_H   = 0.105   # individual query-box height
    Q_GAP = 0.014   # gap between query boxes
    Q_SPAN = N_Q * Q_H + (N_Q - 1) * Q_GAP            # total vertical span
    Q_BOT_CY = MOD_CEN - Q_SPAN / 2 + Q_H / 2         # centre of bottom box
    Q_CYS = [Q_BOT_CY + i * (Q_H + Q_GAP)
             for i in range(N_Q)][::-1]                 # top → bottom order

    # ── Local helpers ────────────────────────────────────────────────────────

    def module_panel(cx, w_half, fill, edge,
                     header_txt, body_txt,
                     h_sz=9.2, b_sz=7.8, lw=2.0, rad=0.013, zord=3):
        """
        Draw a full-height module panel with:
          • Rounded outer box
          • Bold header text near the top
          • Thin separator line
          • Body text below the separator
        All modules use the same vertical extents (MOD_TOP / MOD_BOT).
        """
        left = cx - w_half
        box = FancyBboxPatch(
            (left, MOD_BOT), 2 * w_half, MOD_H,
            boxstyle=f'round,pad={rad}',
            facecolor=fill, edgecolor=edge, linewidth=lw, zorder=zord)
        ax.add_patch(box)

        # Header text at top (inside box)
        h_y = MOD_TOP - 0.038
        ax.text(cx, h_y, header_txt,
                ha='center', va='top', fontsize=h_sz, weight='bold',
                color=edge, zorder=zord + 1, multialignment='center')

        # Separator
        sep_y = h_y - 0.052
        ax.plot([left + 0.006, left + 2 * w_half - 0.006],
                [sep_y, sep_y],
                color=edge, lw=0.9, alpha=0.55, zorder=zord + 1)

        # Body text
        ax.text(cx, sep_y - 0.016, body_txt,
                ha='center', va='top', fontsize=b_sz,
                color='#1A1A2E', zorder=zord + 1, multialignment='center',
                linespacing=1.50)

    def arr(x1, y1, x2, y2, lw=2.2, head=15, clr=ARROW, zord=5):
        """Draw a solid arrowhead from (x1, y1) to (x2, y2)."""
        ax.annotate(
            '', xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle='->', color=clr,
                            lw=lw, mutation_scale=head),
            zorder=zord)

    # ── Title ────────────────────────────────────────────────────────────────
    ax.text(0.500, 0.965,
            'OpenMRS Clinical Chatbot System:  Architecture, Flow, and Safety Logic',
            ha='center', va='center', fontsize=16, weight='bold',
            color=NAVY, zorder=6)
    ax.plot([0.020, 0.980], [0.945, 0.945], color=BLUE, lw=1.8, zorder=5)

    # ════════════════════════════════════════════════════════════════════════
    # MODULE 1 – USER INPUT
    # ════════════════════════════════════════════════════════════════════════
    module_panel(M1cx, M1hw, BLU_F, BLUE,
                 '1. User Input\n(Natural Language)',
                 'Doctor\nPatient\nParent\n\nAny clinical or\ncare query in\nplain text')

    # Arrow 1 → 2
    arr(M1cx + M1hw, MOD_CEN, M2cx - M2hw, MOD_CEN)

    # ════════════════════════════════════════════════════════════════════════
    # MODULE 2 – TRIAGE AGENT
    # ════════════════════════════════════════════════════════════════════════
    module_panel(M2cx, M2hw, BLU_F, BLUE,
                 '2. Triage Agent\n(Intent Classification)',
                 '• Classifies query\n  intent (11 types)\n'
                 '• Detects user role:\n  doctor / patient\n'
                 '• Extracts patient ID,\n  drug/vaccine names\n'
                 '• Returns:\n  (user_type, intent,\n   patient_id, confidence)')

    # ════════════════════════════════════════════════════════════════════════
    # "3. Intent Routing" label + fan arrows  (Triage → each query box)
    # ════════════════════════════════════════════════════════════════════════
    route_lx = (M2cx + M2hw + QXcx - QXhw) / 2
    ax.text(route_lx, MOD_TOP + 0.028,
            '3. Intent Routing',
            ha='center', va='center', fontsize=9.2, weight='bold',
            color=BLUE, zorder=6)

    # Fan: one arrow per query box, all from right edge of Triage Agent
    for qcy in Q_CYS:
        ax.annotate(
            '', xy=(QXcx - QXhw, qcy), xytext=(M2cx + M2hw, MOD_CEN),
            arrowprops=dict(arrowstyle='->', color=ARROW,
                            lw=1.8, mutation_scale=12),
            zorder=5)

    # ════════════════════════════════════════════════════════════════════════
    # QUERY TYPE BOXES (6 stacked)
    # ════════════════════════════════════════════════════════════════════════
    Q_DEFS = [
        ('Medication Query',
         'Drug Dosage Handler\nMedication Allergy Checker'),
        ('Allergy Query',
         'Medication Allergy\nChecker'),
        ('Immunization Query',
         'Immunization Status\nHandler'),
        ('Vitals Query',
         'Vitals Trend Handler'),
        ('Patient Record Query',
         'Record Summary\nHandler'),
        ('Hybrid Query',
         'Hybrid Handler'),
    ]

    for i, ((qtitle, qbody), qcy) in enumerate(zip(Q_DEFS, Q_CYS)):
        qf, qe = Q_COL[i]
        qbox = FancyBboxPatch(
            (QXcx - QXhw, qcy - Q_H / 2), 2 * QXhw, Q_H,
            boxstyle='round,pad=0.009',
            facecolor=qf, edgecolor=qe, linewidth=1.8, zorder=3)
        ax.add_patch(qbox)

        # Title (bold) + subtitle (normal) inside query box
        ax.text(QXcx, qcy + Q_H * 0.20, qtitle,
                ha='center', va='center', fontsize=8.8, weight='bold',
                color=qe, zorder=4, multialignment='center')
        ax.text(QXcx, qcy - Q_H * 0.16, qbody,
                ha='center', va='center', fontsize=7.4,
                color='#1A1A2E', zorder=4, multialignment='center',
                linespacing=1.35)

        # ── Arrow: this query box → Module 4 (Data Retrieval) ────────────
        arr(QXcx + QXhw, qcy, M4cx - M4hw, qcy, lw=1.8, head=11)

    # ════════════════════════════════════════════════════════════════════════
    # MODULE 4 – DATA RETRIEVAL LAYER
    #   FIX: title placed INSIDE the container at the top (not below it)
    # ════════════════════════════════════════════════════════════════════════
    m4_box = FancyBboxPatch(
        (M4cx - M4hw, MOD_BOT), 2 * M4hw, MOD_H,
        boxstyle='round,pad=0.013',
        facecolor=BLU_F, edgecolor=BLUE, linewidth=2.2, zorder=3)
    ax.add_patch(m4_box)

    # Title INSIDE the box (top area)
    m4_title_y = MOD_TOP - 0.038
    ax.text(M4cx, m4_title_y,
            '4. Data Retrieval Layer',
            ha='center', va='top', fontsize=9.2, weight='bold',
            color=BLUE, zorder=4)

    # Separator below title
    m4_sep_y = m4_title_y - 0.052
    ax.plot([M4cx - M4hw + 0.007, M4cx + M4hw - 0.007],
            [m4_sep_y, m4_sep_y],
            color=BLUE, lw=1.0, alpha=0.55, zorder=4)

    # Three sub-boxes (evenly filling the remaining vertical space)
    sub4_items = [
        ('JSON MCP DBs\n(Knowledge Base)',
         'Drug KB  •  Immunization KB\nMilestones KB'),
        ('ChromaDB Vector Store\n(PDF Guidelines)',
         'WHO Medicines  •  CDC\nMilestone Checklists'),
        ('Knowledge Agent\n(Semantic Search)',
         'Embeds queries  •  Returns\nrelevant passages'),
    ]
    sub4_w  = 2 * M4hw - 0.022
    avail4  = m4_sep_y - MOD_BOT - 0.018
    sub4_h  = (avail4 - 2 * 0.014) / 3
    sub4_top0 = m4_sep_y - 0.010   # top edge of first sub-box

    for k, (stitle, sbody) in enumerate(sub4_items):
        sb_top = sub4_top0 - k * (sub4_h + 0.014)
        sb_cy  = sb_top - sub4_h / 2
        sbox = FancyBboxPatch(
            (M4cx - sub4_w / 2, sb_top - sub4_h), sub4_w, sub4_h,
            boxstyle='round,pad=0.006',
            facecolor='#D6EEF8', edgecolor=BLUE,
            linewidth=1.4, zorder=4)
        ax.add_patch(sbox)
        ax.text(M4cx, sb_cy + sub4_h * 0.22, stitle,
                ha='center', va='center', fontsize=8.0, weight='bold',
                color=BLUE, zorder=5, multialignment='center')
        ax.text(M4cx, sb_cy - sub4_h * 0.14, sbody,
                ha='center', va='center', fontsize=7.2,
                color='#1A1A2E', zorder=5, multialignment='center',
                linespacing=1.32)

    # ── Arrow 4 → 5 ──────────────────────────────────────────────────────────
    arr(M4cx + M4hw, MOD_CEN, M5cx - M5hw, MOD_CEN)

    # ════════════════════════════════════════════════════════════════════════
    # MODULE 5 – VALIDATION AGENT
    #   FIX: arrow drawn from Module 4 (above) and to Module 6 (below)
    # ════════════════════════════════════════════════════════════════════════
    module_panel(M5cx, M5hw, BLU_F, BLUE,
                 '5. Validation Agent\n(Safety Layer)',
                 '• Verifies data exists\n'
                 '• Prevents hallucination\n'
                 '• Checks database\n  connectivity\n'
                 '• Validates patient IDs\n'
                 '• Ensures no empty\n  response')

    # ── Arrow 5 → 6 ──────────────────────────────────────────────────────────
    arr(M5cx + M5hw, MOD_CEN, M6cx - M6hw, MOD_CEN)

    # ════════════════════════════════════════════════════════════════════════
    # MODULE 6 – RESPONSE AGENT
    #   Contains two sub-panels: Doctor Response + Patient Response
    #   FIX: arrow drawn from Module 5 (above) and to Module 7 (below)
    # ════════════════════════════════════════════════════════════════════════
    m6_box = FancyBboxPatch(
        (M6cx - M6hw, MOD_BOT), 2 * M6hw, MOD_H,
        boxstyle='round,pad=0.013',
        facecolor=BLU_F, edgecolor=BLUE, linewidth=2.0, zorder=3)
    ax.add_patch(m6_box)

    m6_title_y = MOD_TOP - 0.038
    ax.text(M6cx, m6_title_y,
            '6. Response Agent\n(Formatting by Role)',
            ha='center', va='top', fontsize=9.2, weight='bold',
            color=BLUE, zorder=4, multialignment='center')

    m6_sep_y = m6_title_y - 0.058
    ax.plot([M6cx - M6hw + 0.007, M6cx + M6hw - 0.007],
            [m6_sep_y, m6_sep_y],
            color=BLUE, lw=1.0, alpha=0.55, zorder=4)

    # Two response sub-boxes
    s6w    = 2 * M6hw - 0.020
    avail6 = m6_sep_y - MOD_BOT - 0.018
    s6h    = (avail6 - 0.016) / 2
    dr_top = m6_sep_y - 0.010
    dr_cy  = dr_top - s6h / 2

    dr_box = FancyBboxPatch(
        (M6cx - s6w / 2, dr_top - s6h), s6w, s6h,
        boxstyle='round,pad=0.006',
        facecolor='#DBEAFE', edgecolor=BLUE, linewidth=1.4, zorder=4)
    ax.add_patch(dr_box)
    ax.text(M6cx, dr_cy + s6h * 0.24, 'Doctor Response',
            ha='center', va='center', fontsize=8.0, weight='bold',
            color=BLUE, zorder=5)
    ax.text(M6cx, dr_cy - s6h * 0.12,
            'Clinical detail, IDs,\nsafety notes,\nprofessional look',
            ha='center', va='center', fontsize=7.2,
            color='#1A1A2E', zorder=5, multialignment='center',
            linespacing=1.30)

    pt_top = dr_top - s6h - 0.016
    pt_cy  = pt_top - s6h / 2
    pt_box = FancyBboxPatch(
        (M6cx - s6w / 2, pt_top - s6h), s6w, s6h,
        boxstyle='round,pad=0.006',
        facecolor='#FAD7A0', edgecolor='#E67E22', linewidth=1.4, zorder=4)
    ax.add_patch(pt_box)
    ax.text(M6cx, pt_cy + s6h * 0.24, 'Patient Response',
            ha='center', va='center', fontsize=8.0, weight='bold',
            color='#B7770D', zorder=5)
    ax.text(M6cx, pt_cy - s6h * 0.12,
            'Simplified language,\nparent-friendly,\nsoft color accent',
            ha='center', va='center', fontsize=7.2,
            color='#1A1A2E', zorder=5, multialignment='center',
            linespacing=1.30)

    # ── Arrow 6 → 7 ──────────────────────────────────────────────────────────
    arr(M6cx + M6hw, MOD_CEN, M7cx - M7hw, MOD_CEN)

    # ════════════════════════════════════════════════════════════════════════
    # MODULE 7 – USER OUTPUT
    #   FIX: arrow drawn from Module 6 (above)
    # ════════════════════════════════════════════════════════════════════════
    module_panel(M7cx, M7hw, BLU_F, BLUE,
                 '7. User Output\n(Formatted)',
                 'Structured JSON\nresponse\n\n'
                 '• Saved to\n  responses.json\n'
                 '• Logged for\n  audit trail')

    # ════════════════════════════════════════════════════════════════════════
    # BOTTOM CAPTION
    # ════════════════════════════════════════════════════════════════════════
    ax.plot([0.020, 0.980], [0.068, 0.068], color=BLUE, lw=1.2, zorder=5)
    ax.text(0.500, 0.042,
            'OpenMRS Clinical Chatbot: Modular NLP system routes clinical queries '
            'for doctors and patients, performs real-time data retrieval, validation, '
            'and safety checks,\nand formats responses for clinical and patient use'
            '—ensuring auditability and patient safety.',
            ha='center', va='center', fontsize=8.8,
            color=NAVY, weight='bold', zorder=6, multialignment='center')

    # ════════════════════════════════════════════════════════════════════════
    # SAVE
    # ════════════════════════════════════════════════════════════════════════
    plt.tight_layout(pad=0.3)
    out_path = os.path.join(OUTPUT_DIR, 'flowchart3_architecture_flow.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight',
                facecolor=WHITE, edgecolor='none')
    plt.close(fig)
    print(f'Saved: {out_path}')


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    make_flowchart1()
    make_flowchart2()
    make_flowchart3()
    print('All three flowcharts generated successfully.')
