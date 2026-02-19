"""
Generate coverage analysis tables from language converter coverage results.

This script aggregates coverage results and generates:
1. Table 13 style output (Attack Type | Avg Indescribable | Examples)
2. CSV exports for further analysis
3. LaTeX table for paper

Usage:
    python generate_coverage_tables.py \
        --results_dir language_converter_coverage_analysis/results \
        --output_format latex
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List
import pandas as pd


def load_coverage_results(results_dir: str) -> List[Dict]:
    """Load all coverage result JSON files."""
    results_path = Path(results_dir)
    results = []
    
    for json_file in results_path.glob("*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            results.append(json.load(f))
    
    return results


def extract_privacy_taxonomy(attack_name: str) -> str:
    """Extract privacy taxonomy from attack name (reuses results_analysis logic)."""
    if not attack_name:
        return "unknown"
    
    if attack_name.startswith('related_and_useful'):
        return 'Related And Useful'
    elif attack_name.startswith('related_but_private'):
        return 'Related But Private'
    elif attack_name.startswith('unrelated'):
        return 'Unrelated'
    else:
        return 'unknown'


def extract_security_category(attack_name: str) -> str:
    """Extract security category from attack name (reuses results_analysis logic)."""
    if not attack_name:
        return "unknown"
    
    attack_lower = attack_name.lower()
    
    # DoS attacks
    if any(keyword in attack_lower for keyword in ['dos', 'denial', 'cancel', 'delete', 'disrupt']):
        return 'DoS'
    
    # Email manipulation
    if any(keyword in attack_lower for keyword in ['email', 'forward', 'fraud', 'phishing']):
        return 'Email Manipulation'
    
    # Upselling
    if any(keyword in attack_lower for keyword in ['upsell', 'upgrade', 'premium', 'expensive', 'unnecessary']):
        return 'Upselling'
    
    # Default: try to extract from name pattern (e.g., financial_manipulation_attack_4)
    parts = attack_name.split('_')
    if len(parts) >= 3 and parts[-2] == 'attack' and parts[-1].isdigit():
        category = '_'.join(parts[:-2])
        # Map to high-level categories
        if 'manipulation' in category or 'exploit' in category:
            return 'Upselling'
        else:
            return 'DoS'
    
    return 'unknown'


def group_by_attack_category(results: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Group results by attack type and category.
    
    Uses attack_type (privacy, security, benign_easy) as primary grouping.
    For privacy/security attacks, further groups by taxonomy/category.
    """
    grouped = defaultdict(list)
    
    for result in results:
        attack_type = result.get("attack_type", "unknown")
        attack_name = result.get("attack_name", "")
        
        # Combine benign types
        if attack_type in ["benign_easy", "benign_hard"]:
            group_key = "Benign"
        elif attack_type == "privacy":
            # Group by privacy taxonomy
            taxonomy = extract_privacy_taxonomy(attack_name)
            group_key = f"Privacy - {taxonomy}"
        elif attack_type == "security":
            # Group by security category
            category = extract_security_category(attack_name)
            group_key = f"Security - {category}"
        else:
            group_key = attack_type.capitalize() if attack_type else "Unknown"
        
        grouped[group_key].append(result)
    
    return grouped


def calculate_attack_statistics(results: List[Dict]) -> Dict:
    """Calculate statistics for a group of results."""
    if not results:
        return {
            "count": 0,
            "avg_indescribable": 0.0,
            "avg_describable": 0.0,
            "avg_coverage": 0.0,
            "example_indescribable_items": []
        }
    
    indescribable_counts = []
    describable_counts = []
    all_indescribable_items = []
    
    for result in results:
        if "error" in result:
            continue
        
        indescribable_counts.append(result.get("indescribable_count", 0))
        describable_counts.append(result.get("describable_count", 0))
        
        # Collect indescribable items
        items = result.get("indescribable_items", [])
        all_indescribable_items.extend(items)
    
    if not indescribable_counts:
        return {
            "count": 0,
            "avg_indescribable": 0.0,
            "avg_describable": 0.0,
            "avg_coverage": 0.0,
            "example_indescribable_items": []
        }
    
    avg_indes = sum(indescribable_counts) / len(indescribable_counts)
    avg_desc = sum(describable_counts) / len(describable_counts)
    
    # Get top 3 most common indescribable items
    item_counts = defaultdict(int)
    for item in all_indescribable_items:
        item_counts[item] += 1
    
    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    example_items = [item[0] for item in top_items]
    
    return {
        "count": len(results),
        "avg_indescribable": avg_indes,
        "avg_describable": avg_desc,
        "avg_coverage": (avg_desc / (avg_indes + avg_desc) * 100) if (avg_indes + avg_desc) > 0 else 100.0,
        "example_indescribable_items": example_items
    }


def generate_summary_table(grouped_results: Dict[str, List[Dict]]) -> pd.DataFrame:
    """Generate summary table similar to Table 13."""
    rows = []
    
    for attack_category, results in sorted(grouped_results.items()):
        stats = calculate_attack_statistics(results)
        
        rows.append({
            "Attack Type": attack_category,
            "Count": stats["count"],
            "Avg Indescribable": f"{stats['avg_indescribable']:.2f}",
            "Avg Describable": f"{stats['avg_describable']:.2f}",
            "Coverage %": f"{stats['avg_coverage']:.1f}",
            "Example Indescribable Items": str(stats["example_indescribable_items"])
        })
    
    return pd.DataFrame(rows)


def generate_latex_table(df: pd.DataFrame) -> str:
    """Generate LaTeX table code similar to Table 13 in paper."""
    latex = []
    
    latex.append("\\begin{table}[h]")
    latex.append("\\centering")
    latex.append("\\caption{Average number of indescribable items per attack type (privacy and security) and the benign case}")
    latex.append("\\label{tab:language_converter_coverage}")
    latex.append("\\begin{tabular}{lrp{8cm}}")
    latex.append("\\toprule")
    latex.append("\\textbf{Attack Type} & \\textbf{Avg Indescribable} & \\textbf{Examples of Indescribable Items} \\\\")
    latex.append("\\midrule")
    
    for _, row in df.iterrows():
        attack_type = row["Attack Type"]
        avg_indes = row["Avg Indescribable"]
        
        # Parse example items
        examples_str = row["Example Indescribable Items"]
        try:
            examples = eval(examples_str)  # Convert string representation of list
            examples_formatted = ", ".join(f"'{item}'" for item in examples[:3])
            examples_formatted = f"[{examples_formatted}]"
        except:
            examples_formatted = examples_str
        
        latex.append(f"{attack_type} & {avg_indes} & {examples_formatted} \\\\")
    
    latex.append("\\bottomrule")
    latex.append("\\end{tabular}")
    latex.append("\\end{table}")
    
    return "\n".join(latex)


def main():
    parser = argparse.ArgumentParser(description="Generate language converter coverage analysis tables")
    
    parser.add_argument(
        "--results_dir",
        type=str,
        default="language_converter_coverage_analysis/results",
        help="Directory containing coverage result JSON files"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="language_converter_coverage_analysis",
        help="Directory to save output tables"
    )
    parser.add_argument(
        "--output_format",
        type=str,
        choices=["csv", "latex", "both"],
        default="both",
        help="Output format for tables"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("LANGUAGE CONVERTER COVERAGE TABLE GENERATION")
    print("=" * 80)
    print(f"Results directory: {args.results_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Output format: {args.output_format}")
    print("=" * 80)
    print()
    
    # Load results
    print("📂 Loading coverage results...")
    results = load_coverage_results(args.results_dir)
    print(f"   Loaded {len(results)} result files")
    print()
    
    if not results:
        print("❌ No results found. Run run_coverage_analysis.py first.")
        return
    
    # Group by attack category
    print("📊 Grouping results by attack type...")
    grouped_results = group_by_attack_category(results)
    
    for category, items in grouped_results.items():
        print(f"   {category}: {len(items)} results")
    print()
    
    # Generate summary table
    print("📋 Generating summary table...")
    summary_df = generate_summary_table(grouped_results)
    print()
    print(summary_df.to_string(index=False))
    print()
    
    # Save outputs
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    if args.output_format in ["csv", "both"]:
        csv_file = output_path / "language_converter_coverage_summary.csv"
        summary_df.to_csv(csv_file, index=False)
        print(f"✅ CSV saved to: {csv_file}")
    
    if args.output_format in ["latex", "both"]:
        latex_file = output_path / "language_converter_coverage_table.tex"
        latex_content = generate_latex_table(summary_df)
        
        with open(latex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        print(f"✅ LaTeX table saved to: {latex_file}")
    
    print()
    print("=" * 80)
    print("TABLE GENERATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
