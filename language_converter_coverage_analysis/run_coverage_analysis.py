"""
Main script to run language converter coverage analysis on existing experiment logs.

This script:
1. Scans existing conversation logs for specified modes
2. Evaluates how well the language converter template covers external agent communications
3. Saves results for later aggregation and table generation

Usage:
    python run_coverage_analysis.py \
        --logs_dir logs \
        --mode firewalls_data_abstraction_language_converter \
        --use_cases travel_planning,real_estate,insurance \
        --judge_llm_name gpt-5-chat-latest \
        --judge_provider openai
"""

import argparse
import json
import random
from pathlib import Path
from tqdm import tqdm

from language_converter_coverage_judge import LanguageConverterCoverageJudge, evaluate_single_file
from language_converter_coverage_utils import (
    find_conversation_files,
    parse_conversation_path,
    save_coverage_result
)


def main():
    parser = argparse.ArgumentParser(description="Run language converter coverage analysis on existing logs")
    
    # Input/output paths
    parser.add_argument(
        "--logs_dir",
        type=str,
        default="logs",
        help="Base directory containing experiment logs"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="language_converter_coverage_analysis/results",
        help="Directory to save coverage results"
    )
    parser.add_argument(
        "--templates_dir",
        type=str,
        default="mitigation_guidelines/generated",
        help="Directory containing language converter templates"
    )
    
    # Filtering
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        help="Mode to analyze (e.g., firewalls_data_abstraction_language_converter)"
    )
    parser.add_argument(
        "--use_cases",
        type=str,
        default=None,
        help="Comma-separated list of use cases to analyze (e.g., travel_planning,real_estate)"
    )
    parser.add_argument(
        "--models",
        type=str,
        default=None,
        help="Comma-separated list of models to analyze (optional filter)"
    )
    parser.add_argument(
        "--personas",
        type=str,
        default=None,
        help="Comma-separated list of persona numbers to analyze (e.g., '1,2,3')"
    )
    
    # Judge configuration
    parser.add_argument(
        "--judge_llm_name",
        type=str,
        required=True,
        help="LLM to use for coverage evaluation"
    )
    parser.add_argument(
        "--judge_provider",
        type=str,
        default=None,
        help="Provider for judge LLM (azure, openai, anthropic, etc.)"
    )
    parser.add_argument(
        "--judge_max_retries",
        type=int,
        default=3,
        help="Maximum retries for judge LLM calls"
    )
    parser.add_argument(
        "--use_azure_credentials",
        action="store_true",
        help="Use Azure DefaultAzureCredential instead of API key for Azure OpenAI"
    )
    
    # Processing options
    parser.add_argument(
        "--skip_existing",
        action="store_true",
        help="Skip files that already have coverage results"
    )
    
    # Sampling options
    parser.add_argument(
        "--num_privacy_samples",
        type=int,
        default=None,
        help="Number of privacy attacks to sample per persona (None = all)"
    )
    parser.add_argument(
        "--num_security_samples",
        type=int,
        default=None,
        help="Number of security attacks to sample per persona (None = all)"
    )
    parser.add_argument(
        "--sampling_seed",
        type=int,
        default=42,
        help="Random seed for attack sampling (for reproducibility)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output showing what's sent to judge LLM"
    )
    
    args = parser.parse_args()
    
    # Parse use cases filter
    use_cases_filter = args.use_cases.split(",") if args.use_cases else None
    models_filter = args.models.split(",") if args.models else None
    personas_filter = args.personas.split(",") if args.personas else None
    
    print("=" * 80)
    print("LANGUAGE CONVERTER COVERAGE ANALYSIS")
    print("=" * 80)
    print(f"Logs directory: {args.logs_dir}")
    print(f"Mode: {args.mode}")
    print(f"Use cases: {use_cases_filter if use_cases_filter else 'All'}")
    print(f"Models: {models_filter if models_filter else 'All'}")
    print(f"Personas: {personas_filter if personas_filter else 'All'}")
    print(f"Judge LLM: {args.judge_llm_name} ({args.judge_provider or 'auto-detect'})")
    print(f"Output directory: {args.output_dir}")
    print("=" * 80)
    print()
    
    # Find conversation files
    print("🔍 Scanning for conversation files...")
    conversation_files = find_conversation_files(args.logs_dir, args.mode, use_cases_filter)
    
    # Filter by model if specified
    if models_filter:
        filtered_files = []
        for file_path in conversation_files:
            try:
                metadata = parse_conversation_path(file_path, args.logs_dir)
                if metadata["model"] in models_filter:
                    filtered_files.append(file_path)
            except Exception:
                continue
        conversation_files = filtered_files
    
    # Filter by persona if specified
    if personas_filter:
        filtered_files = []
        for file_path in conversation_files:
            try:
                metadata = parse_conversation_path(file_path, args.logs_dir)
                if metadata["persona"] in personas_filter:
                    filtered_files.append(file_path)
            except Exception:
                continue
        conversation_files = filtered_files
    
    print(f"   Found {len(conversation_files)} conversation files")
    
    # Apply sampling if requested
    if args.num_privacy_samples is not None or args.num_security_samples is not None:
        print(f"\n🎲 Applying sampling (seed={args.sampling_seed})...")
        print("   Sampling per (persona, use_case) combination...")
        
        # Group files by (persona, use_case, attack_type)
        from collections import defaultdict
        grouped_files = defaultdict(lambda: {"privacy": [], "security": [], "benign": [], "other": []})
        
        for file_path in conversation_files:
            try:
                metadata = parse_conversation_path(file_path, args.logs_dir)
                persona = metadata.get("persona", "unknown")
                use_case = metadata.get("use_case", "unknown")
                attack_type = metadata.get("attack_type", "")
                
                key = (persona, use_case)
                
                if attack_type == "privacy":
                    grouped_files[key]["privacy"].append(file_path)
                elif attack_type == "security":
                    grouped_files[key]["security"].append(file_path)
                elif attack_type.startswith("benign"):
                    grouped_files[key]["benign"].append(file_path)
                else:
                    grouped_files[key]["other"].append(file_path)
            except Exception:
                grouped_files[("unknown", "unknown")]["other"].append(file_path)
        
        # Sample within each group
        sampled_files = []
        random.seed(args.sampling_seed)
        
        for (persona, use_case), files_dict in sorted(grouped_files.items()):
            privacy_count = len(files_dict["privacy"])
            security_count = len(files_dict["security"])
            benign_count = len(files_dict["benign"])
            other_count = len(files_dict["other"])
            
            print(f"\n   [{use_case} / persona {persona}]")
            print(f"      Privacy: {privacy_count}, Security: {security_count}, Benign: {benign_count}")
            
            # Sample privacy
            privacy_sampled = files_dict["privacy"]
            if args.num_privacy_samples is not None and len(privacy_sampled) > args.num_privacy_samples:
                privacy_sampled = random.sample(privacy_sampled, args.num_privacy_samples)
                print(f"      → Sampled {len(privacy_sampled)} privacy attacks")
            
            # Sample security
            security_sampled = files_dict["security"]
            if args.num_security_samples is not None and len(security_sampled) > args.num_security_samples:
                security_sampled = random.sample(security_sampled, args.num_security_samples)
                print(f"      → Sampled {len(security_sampled)} security attacks")
            
            # Keep all benign and other files
            sampled_files.extend(privacy_sampled)
            sampled_files.extend(security_sampled)
            sampled_files.extend(files_dict["benign"])
            sampled_files.extend(files_dict["other"])
        
        conversation_files = sampled_files
        print(f"\n   Total after sampling: {len(conversation_files)} files")
    
    if not conversation_files:
        print("❌ No conversation files found. Exiting.")
        return
    
    print()
    
    # Initialize judge
    print(f"🤖 Initializing judge: {args.judge_llm_name}...")
    judge = LanguageConverterCoverageJudge(
        llm_name=args.judge_llm_name,
        provider=args.judge_provider,
        use_azure_credentials=args.use_azure_credentials,
        debug=args.debug
    )
    print("   ✅ Judge initialized")
    if args.debug:
        print("   🐛 DEBUG MODE ENABLED")
    print()
    
    # Process files
    print(f"📊 Processing {len(conversation_files)} files...")
    print()
    
    results_summary = {
        "total": len(conversation_files),
        "processed": 0,
        "skipped": 0,
        "errors": 0,
        "avg_indescribable": [],
        "avg_describable": []
    }
    
    for conv_file in tqdm(conversation_files, desc="Evaluating coverage"):
        try:
            # Parse metadata
            metadata = parse_conversation_path(conv_file, args.logs_dir)
            
            # Check if already processed
            if args.skip_existing:
                expected_filename = (
                    f"{metadata['use_case']}_{metadata['model']}_{metadata['mode']}_"
                    f"persona{metadata['persona']}_{metadata['attack_name']}_rep{metadata['repetition']}.json"
                )
                output_file = Path(args.output_dir) / expected_filename
                
                if output_file.exists():
                    results_summary["skipped"] += 1
                    continue
            
            # Evaluate
            result = evaluate_single_file(
                str(conv_file),
                metadata["use_case"],
                judge,
                args.templates_dir
            )
            
            # Save result
            output_path = save_coverage_result(result, args.output_dir, metadata)
            
            # Update summary
            results_summary["processed"] += 1
            if "error" not in result:
                results_summary["avg_indescribable"].append(result["indescribable_count"])
                results_summary["avg_describable"].append(result["describable_count"])
            else:
                results_summary["errors"] += 1
            
        except Exception as e:
            print(f"\n❌ Error processing {conv_file}: {e}")
            results_summary["errors"] += 1
            continue
    
    print()
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print(f"Total files: {results_summary['total']}")
    print(f"Processed: {results_summary['processed']}")
    print(f"Skipped: {results_summary['skipped']}")
    print(f"Errors: {results_summary['errors']}")
    
    if results_summary['avg_indescribable']:
        avg_indes = sum(results_summary['avg_indescribable']) / len(results_summary['avg_indescribable'])
        avg_desc = sum(results_summary['avg_describable']) / len(results_summary['avg_describable'])
        print(f"\nAverage indescribable items: {avg_indes:.2f}")
        print(f"Average describable items: {avg_desc:.2f}")
        print(f"Average coverage: {(avg_desc / (avg_indes + avg_desc) * 100):.1f}%")
    
    print(f"\nResults saved to: {args.output_dir}")
    print("\nNext step: Run generate_coverage_tables.py to create analysis tables")
    print("=" * 80)


if __name__ == "__main__":
    main()
