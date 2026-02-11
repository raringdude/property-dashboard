#!/usr/bin/env python3
"""
Pre-Lease Property Report Generator

Generates a dark-themed HTML dashboard from CSV data.

Usage:
    python generate_report.py                    # Uses default 'Pre-Lease - Summary.csv'
    python generate_report.py data.csv           # Uses specified CSV file
    python generate_report.py --sample           # Generate report with sample data
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader


def load_data(csv_path: str | None = None) -> pd.DataFrame:
    """Load data from CSV or generate sample data if file not found."""

    if csv_path and os.path.exists(csv_path):
        df = pd.read_csv(csv_path)

        # Map actual CSV columns to expected names
        column_mapping = {
            'Unit Type': 'unit_type',
            'Rentable Units': 'total_units',
            'Pre-Leased - Total': 'preleased',
            'Pre-Leased - New Lease': 'new_leases',
            'Pre-Leased - Renewal': 'renewals',
            'Pre-Leased - %': 'occupancy_pct',
            'Projected Availability': 'available'
        }

        df = df.rename(columns=column_mapping)

        # Filter out rows with 0 total units (like "Not Selected")
        df = df[df['total_units'] > 0].copy()

        return df

    # Sample data matching the plan specs (600 total units, 170 projected availability)
    print("CSV not found. Using sample data for demonstration.")
    return pd.DataFrame({
        'unit_type': ['Studio', '1BR', '1BR+Den', '2BR', '2BR+Den', '3BR'],
        'total_units': [80, 150, 100, 140, 80, 50],
        'preleased': [72, 120, 82, 112, 60, 44],
        'available': [8, 30, 18, 28, 20, 6],
        'new_leases': [45, 70, 50, 65, 35, 25],
        'renewals': [27, 50, 32, 47, 25, 19]
    })


def calculate_metrics(df: pd.DataFrame) -> dict:
    """Calculate summary metrics from the data."""

    total_units = int(df['total_units'].sum())
    total_preleased = int(df['preleased'].sum())
    total_available = int(df['available'].sum())
    overall_occupancy = round((total_preleased / total_units) * 100, 1) if total_units > 0 else 0

    return {
        'total_units': total_units,
        'total_preleased': total_preleased,
        'total_available': total_available,
        'overall_occupancy': overall_occupancy
    }


def prepare_chart_data(df: pd.DataFrame) -> dict:
    """Prepare data for all Plotly charts."""

    # Calculate occupancy percentage for each unit type if not already present
    if 'occupancy_pct' not in df.columns:
        df['occupancy_pct'] = round((df['preleased'] / df['total_units']) * 100, 1)
    else:
        # Convert from decimal (0.82) to percentage (82.0) if needed
        if df['occupancy_pct'].max() <= 1:
            df['occupancy_pct'] = round(df['occupancy_pct'] * 100, 1)

    # Sort by occupancy for the bar chart
    df_sorted = df.sort_values('occupancy_pct', ascending=True)

    # Horizontal bar chart data (Pre-Lease % by Unit Type)
    occupancy_chart = {
        'labels': df_sorted['unit_type'].tolist(),
        'values': df_sorted['occupancy_pct'].tolist()
    }

    # Donut chart data (Overall composition)
    total_new = int(df['new_leases'].sum())
    total_renewals = int(df['renewals'].sum())
    total_available = int(df['available'].sum())

    donut_chart = {
        'labels': ['New Leases', 'Renewals', 'Available'],
        'values': [total_new, total_renewals, total_available]
    }

    # Stacked bar chart data (New vs Renewal by unit type)
    stacked_chart = {
        'labels': df['unit_type'].tolist(),
        'new_leases': df['new_leases'].tolist(),
        'renewals': df['renewals'].tolist()
    }

    # Availability chart data
    availability_chart = {
        'labels': df['unit_type'].tolist(),
        'preleased': df['preleased'].tolist(),
        'available': df['available'].tolist()
    }

    return {
        'occupancy_chart': occupancy_chart,
        'donut_chart': donut_chart,
        'stacked_chart': stacked_chart,
        'availability_chart': availability_chart
    }


def prepare_table_data(df: pd.DataFrame) -> list[dict]:
    """Prepare data for the HTML table with conditional formatting."""

    # Calculate occupancy percentage if not already present
    if 'occupancy_pct' not in df.columns:
        df['occupancy_pct'] = round((df['preleased'] / df['total_units']) * 100, 1)
    else:
        # Convert from decimal (0.82) to percentage (82.0) if needed
        if df['occupancy_pct'].max() <= 1:
            df['occupancy_pct'] = round(df['occupancy_pct'] * 100, 1)

    table_data = []
    for _, row in df.iterrows():
        occ = row['occupancy_pct']
        if occ < 70:
            occ_class = 'occupancy-low'
        elif occ < 90:
            occ_class = 'occupancy-mid'
        else:
            occ_class = 'occupancy-high'

        table_data.append({
            'unit_type': row['unit_type'],
            'total_units': int(row['total_units']),
            'preleased': int(row['preleased']),
            'available': int(row['available']),
            'new_leases': int(row['new_leases']),
            'renewals': int(row['renewals']),
            'occupancy': occ,
            'occupancy_class': occ_class
        })

    return table_data


def generate_report(csv_path: str | None = None, output_path: str = 'report.html'):
    """Generate the HTML report."""

    # Load data
    df = load_data(csv_path)

    # Calculate all metrics and prepare data
    metrics = calculate_metrics(df)
    charts = prepare_chart_data(df)
    table_data = prepare_table_data(df)

    # Set up Jinja2 template
    template_dir = Path(__file__).parent / 'templates'
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('report.html')

    # Render the template
    html_content = template.render(
        report_date=datetime.now().strftime('%B %d, %Y'),
        total_units=metrics['total_units'],
        overall_occupancy=metrics['overall_occupancy'],
        total_available=metrics['total_available'],
        total_preleased=metrics['total_preleased'],
        occupancy_chart_data=json.dumps(charts['occupancy_chart']),
        donut_chart_data=json.dumps(charts['donut_chart']),
        stacked_chart_data=json.dumps(charts['stacked_chart']),
        availability_chart_data=json.dumps(charts['availability_chart']),
        table_data=table_data
    )

    # Write output
    output_file = Path(output_path)
    output_file.write_text(html_content)

    print(f"Report generated: {output_file.absolute()}")
    print(f"Total Units: {metrics['total_units']}")
    print(f"Overall Pre-Lease: {metrics['overall_occupancy']}%")
    print(f"Projected Availability: {metrics['total_available']}")
    print("\nOpen report.html in a browser to view. Use Cmd+P (Mac) or Ctrl+P (Windows) to print to PDF.")

    return output_file


if __name__ == '__main__':
    # Handle command line arguments
    csv_file = None

    if len(sys.argv) > 1:
        if sys.argv[1] == '--sample':
            csv_file = None  # Will use sample data
        else:
            csv_file = sys.argv[1]
    else:
        # Default CSV filename
        default_csv = 'Pre-Lease - Summary.csv'
        if os.path.exists(default_csv):
            csv_file = default_csv

    generate_report(csv_file)
