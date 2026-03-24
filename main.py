#!/usr/bin/env python3
"""
Legal Contract RAG Chunking Tool

A tool for intelligently splitting legal contract documents into chunks
suitable for Retrieval Augmented Generation (RAG) applications.
"""

import argparse
import json
import os
import sys

from src.processor import ContractProcessor


def main():
    parser = argparse.ArgumentParser(
        description='Legal Contract RAG Chunking Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single PDF file
  python main.py contract.pdf -o output.json

  # Process a DOCX file with custom chunk size
  python main.py contract.docx -o output.json --max-tokens 800

  # Process all files in a directory
  python main.py contracts/ -o output.json

  # Process with verbose output
  python main.py contract.pdf -o output.json -v
        """
    )

    parser.add_argument(
        'input',
        help='Input file or directory containing contract files'
    )

    parser.add_argument(
        '-o', '--output',
        default='output.json',
        help='Output JSON file path (default: output.json)'
    )

    parser.add_argument(
        '--max-tokens',
        type=int,
        default=500,
        help='Maximum tokens per chunk (default: 500)'
    )

    parser.add_argument(
        '--overlap-tokens',
        type=int,
        default=50,
        help='Number of overlapping tokens for context (default: 50)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Validate input
    if not os.path.exists(args.input):
        print(f"Error: Input path does not exist: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Initialize processor
    processor = ContractProcessor(
        max_tokens=args.max_tokens,
        overlap_tokens=args.overlap_tokens
    )

    try:
        if os.path.isdir(args.input):
            if args.verbose:
                print(f"Processing directory: {args.input}")
            chunks = processor.process_batch(args.input)
            if args.verbose:
                print(f"Found {len(chunks)} chunks from batch processing")
        else:
            if args.verbose:
                print(f"Processing file: {args.input}")
            chunks = processor.process(args.input)
            if args.verbose:
                print(f"Generated {len(chunks)} chunks")

        # Write output JSON
        output_data = [chunk.dict() for chunk in chunks]

        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"Successfully wrote {len(chunks)} chunks to {args.output}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
