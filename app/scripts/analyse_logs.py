from re import search
from datetime import datetime
from collections import defaultdict
from argparse import ArgumentParser



def analyze_security_logs(log_file_path):
    """Analyze security logs for suspicious activities"""

    failed_logins = defaultdict(list)
    successful_logins = defaultdict(list)
    # registrations = []

    with open(log_file_path, 'r') as f:
        for line in f:
            if 'Failed login attempt' in line:
                ip_match = search(r'from IP: ([\d.]+)', line)
                email_match = search(r'for: ([^\s]+)', line)
                timestamp_match = search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)

                if ip_match and email_match and timestamp_match:
                    ip = ip_match.group(1)
                    email = email_match.group(1)
                    timestamp = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                    failed_logins[ip].append((email, timestamp))

            elif 'Successful login' in line:
                ip_match = search(r'from IP: ([\d.]+)', line)
                email_match = search(r'for user: ([^\s]+)', line)

                if ip_match and email_match:
                    successful_logins[ip_match.group(1)].append(email_match.group(1))

    # Detect suspicious activities
    print("=== SECURITY ANALYSIS ===")

    # Multiple failed login attempts
    print("\n--- IPs with multiple failed login attempts ---")
    for ip, attempts in failed_logins.items():
        if len(attempts) >= 5:
            print(f"IP {ip}: {len(attempts)} failed attempts")
            for email, timestamp in attempts[-5:]:  # Show last 5
                print(f"  {timestamp}: {email}")

    # Rate limiting hits
    print("\n--- Rate limiting analysis ---")
    # Add rate limiting analysis here

    return failed_logins, successful_logins

if __name__ == "__main__":
    parser = ArgumentParser(description='Analyze N.I.X security logs')
    parser.add_argument('log_file', help='Path to security log file')
    args = parser.parse_args()

    analyze_security_logs(args.log_file)
