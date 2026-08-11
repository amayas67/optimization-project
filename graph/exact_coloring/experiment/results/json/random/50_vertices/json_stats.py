#!/usr/bin/env python3
"""
json_stats.py - Analyze JSON files in current directory
Lists for each algorithm which files it was optimal in and which it wasn't.
Generates a txt file with results.
"""

import json
import os
import sys
from pathlib import Path
from io import StringIO

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None


class JsonStatsAnalyzer:
    """Analyzes JSON files in current directory for algorithm optimality."""
    
    def __init__(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.algorithms = [
            "Greedy", "Welsh-Powell", "DSATUR", "IDO", "RLF",
            "Smallest-degree-last", "Random greedy (×10)", 
            "Simulated Annealing", "Hybrid Evolutionary", "Tabucol",
            "CP-SAT (OR-Tools)", "SAT",
            "Backtracking (exact)"
        ]
        
        self.algo_name_map = {
            "Greedy": "greedy",
            "Welsh-Powell": "welsh_powell",
            "DSATUR": "dsatur",
            "IDO": "ido",
            "RLF": "rlf",
            "Smallest-degree-last": "smallest_degree_last",
            "Random greedy (×10)": "random_greedy",
            "Simulated Annealing": "sa",
            "Hybrid Evolutionary": "hea",
            "Tabucol": "tabu",
            "CP-SAT (OR-Tools)": "cpsat",
            "SAT": "sat",
            "Backtracking (exact)": "backtracking"
        }
        
        self.stats = {algo: {"optimal": [], "non_optimal": []} for algo in self.algorithms}
        self.total_files = 0
        self.all_vertices = []
        
    def scan_current_directory(self):
        """Scan only the current directory for JSON files."""
        print(f"Scanning current directory: {self.current_dir}")
        print()
        
        json_files = []
        for f in os.listdir(self.current_dir):
            if f.endswith('.json'):
                json_files.append(f)
        
        json_files.sort()
        print(f"Found {len(json_files)} JSON files")
        print()
        
        return json_files
    
    def analyze_files(self, json_files):
        """Analyze each JSON file and build statistics."""
        print("Analyzing files...")
        
        for filename in json_files:
            try:
                filepath = os.path.join(self.current_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.total_files += 1
                
                # Get exact chi (ground truth)
                ground_truth = data.get('ground_truth', {})
                exact_chi = ground_truth.get('chi', 0)
                
                # Get vertex count
                instance = data.get('instance', {})
                n_vertices = instance.get('n_vertices', 0)
                self.all_vertices.append(n_vertices)
                
                # Get results
                results = data.get('results', [])
                
                # Find minimum colors used (best non-optimal solution)
                min_colors = min((r.get('n_colors', float('inf')) for r in results), default=float('inf'))
                
                # Check each algorithm
                for algo_display, algo_json in self.algo_name_map.items():
                    algo_result = next((r for r in results if r.get('algorithm') == algo_json), None)
                    
                    if algo_result:
                        n_colors = algo_result.get('n_colors', 0)
                        is_optimal = (n_colors == exact_chi)
                        is_best = (n_colors == min_colors)
                        
                        if is_optimal:
                            self.stats[algo_display]["optimal"].append(filename)
                        else:
                            self.stats[algo_display]["non_optimal"].append(filename)
                
            except Exception as e:
                print(f"  ERROR: Failed to process {filename}: {e}")
        
        print(f"Processed {self.total_files} files successfully")
        print()
    
    def calculate_the_first_ten(self):
        """Calculate 'The first ten' statistics."""
        print("Calculating 'The first ten' statistics...")
        
        first_ten_optimal = []
        first_ten_non_optimal = []
        
        for filename in [f for f in os.listdir(self.current_dir) if f.endswith('.json')]:
            try:
                filepath = os.path.join(self.current_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                ground_truth = data.get('ground_truth', {})
                exact_chi = ground_truth.get('chi', 0)
                results = data.get('results', [])
                
                has_optimal = False
                has_best = False
                all_non_optimal = True
                
                for algo_json_name in ["greedy", "welsh_powell", "dsatur", "ido", "rlf",
                                       "smallest_degree_last", "random_greedy", "sa", 
                                       "hea", "tabu"]:
                    algo_result = next((r for r in results if r.get('algorithm') == algo_json_name), None)
                    
                    if algo_result:
                        n_colors = algo_result.get('n_colors', 0)
                        is_optimal = (n_colors == exact_chi)
                        
                        if is_optimal:
                            has_optimal = True
                            all_non_optimal = False
                
                if has_optimal:
                    first_ten_optimal.append(filename)
                else:
                    first_ten_non_optimal.append(filename)
                    
            except Exception as e:
                print(f"  ERROR: Failed to process {filename}: {e}")
        
        self.stats["The first ten"] = {
            "optimal": first_ten_optimal,
            "non_optimal": first_ten_non_optimal
        }
        
        print(f"  Optimal: {len(first_ten_optimal)} files")
        print(f"  Non-optimal: {len(first_ten_non_optimal)} files")
        print()
        
        # Calculate vertex range
        if self.all_vertices:
            self.min_vertices = min(self.all_vertices)
            self.max_vertices = max(self.all_vertices)
        else:
            self.min_vertices = 0
            self.max_vertices = 0
    
    def display_results(self, output_buffer=None):
        """Display results in command line and optionally write to buffer."""
        # If no buffer provided, just print to stdout
        if output_buffer is None:
            output_buffer = sys.stdout
        
        def print_to_buffer(*args, **kwargs):
            print(*args, file=output_buffer, **kwargs)
        
        print_to_buffer("="*120)
        print_to_buffer("RESULTS - Algorithm Optimality Analysis")
        print_to_buffer("="*120)
        print_to_buffer()
        
        # Display vertex range
        if hasattr(self, 'min_vertices') and hasattr(self, 'max_vertices'):
            if self.min_vertices == self.max_vertices:
                print_to_buffer(f"Vertices: {self.min_vertices} (all files)")
            else:
                print_to_buffer(f"Vertices range: {self.min_vertices} – {self.max_vertices}")
            print_to_buffer()
        
        for algo in self.algorithms + ["The first ten"]:
            optimal_files = sorted(self.stats[algo]["optimal"])
            non_optimal_files = sorted(self.stats[algo]["non_optimal"])
            
            total = len(optimal_files) + len(non_optimal_files)
            if total == 0:
                continue
                
            optimal_count = len(optimal_files)
            non_optimal_count = len(non_optimal_files)
            optimal_pct = (optimal_count / total * 100) if total > 0 else 0.0
            
            print_to_buffer(f"\n{algo}:")
            print_to_buffer(f"  Optimal: {optimal_count}/{total} ({optimal_pct:.1f}%)  |  Non-optimal: {non_optimal_count}/{total}")
            print_to_buffer()
            
            # Display files in horizontal grid layout (3 columns)
            if optimal_files:
                print_to_buffer(f"  ✓ OPTIMAL ({optimal_count} files):")
                self._print_files_in_grid(optimal_files, "    ✓ ", output_buffer)
                print_to_buffer()
            
            if non_optimal_files:
                print_to_buffer(f"  ✗ NON-OPTIMAL ({non_optimal_count} files):")
                self._print_files_in_grid(non_optimal_files, "    ✗ ", output_buffer)
                print_to_buffer()
            
            print_to_buffer("-"*120)
    
    def _print_files_in_grid(self, files, prefix, output_buffer=None):
        """Print files in a horizontal grid layout (3 columns)."""
        cols = 3
        col_width = 38
        rows = (len(files) + cols - 1) // cols
        
        for i in range(rows):
            line = ""
            for j in range(cols):
                idx = i + j * rows
                if idx < len(files):
                    filename = files[idx]
                    line += f"{prefix}{filename:<{col_width - len(prefix)}}"
            
            if output_buffer:
                print(line, file=output_buffer)
            else:
                print(line)
    
    def run(self):
        """Run the analysis."""
        # Print header to console
        print("="*80)
        print("JSON Stats Analyzer")
        print("="*80)
        print()
        
        # Scan and analyze
        json_files = self.scan_current_directory()
        
        if not json_files:
            print("No JSON files found in current directory!")
            return
        
        self.analyze_files(json_files)
        self.calculate_the_first_ten()
        
        # Create a string buffer to capture all output for file
        output_buffer = StringIO()
        
        # Display results to both console (None) and file (output_buffer)
        self.display_results(None)  # Console output
        self.display_results(output_buffer)  # File output
        
        # Display vertex range summary
        if hasattr(self, 'min_vertices') and hasattr(self, 'max_vertices'):
            print()
            if self.min_vertices == self.max_vertices:
                print(f"Vertices: {self.min_vertices} (all files)")
            else:
                print(f"Vertices range: {self.min_vertices} – {self.max_vertices}")
        
        # Write to file
        output_file = os.path.join(self.current_dir, "json_stats_results.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_buffer.getvalue())
        
        print()
        print("="*80)
        print("Summary:")
        print(f"  Total files analyzed: {self.total_files}")
        print(f"  Algorithms checked: {len(self.algorithms) + 1} (including 'The first ten')")
        print(f"  Results saved to: {output_file}")
        print("="*80)


def main():
    """Main entry point."""
    analyzer = JsonStatsAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()