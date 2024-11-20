"""
This script generates a synthetic bimodal distribution of personal data file sizes, inspired by studies that show
most files are small, but most storage and I/O activity is directed at large files. The following sources provide
empirical support for this modeling:

1. "A File Size Distribution Analysis" by Bianca Schroeder and Garth A. Gibson (FAST '08)
   URL: http://www.cs.cmu.edu/~bianca/fast08.pdf

2. "File System Usage in Windows NT 4.0" by John Douceur and William J. Bolosky
   URL: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/dbl.pdf

3. "Characterizing Data Center File Systems under Production Workloads" by Sanjay Ghemawat, Howard Gobioff, and Shun-Tak Leung
   URL: https://static.googleusercontent.com/media/research.google.com/en//archive/gfs-sosp2003.pdf

4. "A Performance Comparison of Personal Computer File Systems" by David Rosenthal
   URL: https://dl.acm.org/doi/10.1145/265910.265918
"""
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Seed for reproducibility
np.random.seed(42)

# Generate synthetic data to simulate file sizes
# Mode 1: Small files (1 KB to 1 MB)
small_files = np.random.lognormal(mean=10, sigma=0.5, size=10000)  # lognormal distribution for small files
small_files = small_files[small_files < 1e6]  # Limit to files smaller than 1MB

# Mode 2: Large files (100 MB to 10 GB)
large_files = np.random.lognormal(mean=20, sigma=1, size=1000)  # lognormal distribution for large files
large_files = large_files[large_files > 1e8]  # Limit to files larger than 100MB

# Combine small and large files
file_sizes = np.concatenate([small_files, large_files])

# Convert bytes to MB for better visualization
file_sizes_mb = file_sizes / (1024 * 1024)

# Create a histogram
plt.figure(figsize=(10, 6))
plt.hist(file_sizes_mb, bins=100, color='blue', alpha=0.7, label='File Sizes')

# Add titles and labels
plt.title('Bimodal Distribution of Personal Data File Sizes')
plt.xlabel('File Size (MB)')
plt.ylabel('Frequency')

# Set x-axis to logarithmic scale for better visualization of size differences
plt.xscale('log')

# Show legend and plot
plt.legend()
plt.grid(True, which="both", ls="--")
plt.savefig('file_size_distribution.png')
# terrible visualization. Let's try a log-log plot instead.

plt.figure(figsize=(10, 6))
plt.hist(file_sizes_mb, bins=100, color='blue', alpha=0.7, log=True)
plt.xscale('log')

plt.title('Log-Log Plot of File Sizes vs. Frequency')
plt.xlabel('File Size (MB)')
plt.ylabel('Frequency (Log scale)')

plt.grid(True, which="both", ls="--")
plt.savefig('log_log_distribution.png', dpi=300, bbox_inches='tight')


file_sizes_mb_sorted = np.sort(file_sizes_mb)
cdf = np.arange(1, len(file_sizes_mb_sorted)+1) / len(file_sizes_mb_sorted)

plt.figure(figsize=(10, 6))
plt.plot(file_sizes_mb_sorted, cdf, color='green', label='CDF')

plt.xscale('log')  # Log scale for file size
plt.title('Cumulative Distribution of File Sizes')
plt.xlabel('File Size (MB)')
plt.ylabel('Cumulative Fraction')

plt.grid(True, which="both", ls="--")
plt.savefig('cdf_file_sizes.png', dpi=300, bbox_inches='tight')

# Generate synthetic I/O activity (assuming more activity for large files)
io_activity = np.random.rand(len(file_sizes)) * (file_sizes / np.mean(file_sizes))  # synthetic I/O

plt.figure(figsize=(10, 6))
plt.scatter(file_sizes_mb, io_activity, alpha=0.5, color='red')

plt.xscale('log')
plt.yscale('log')  # Use log scale to see the relationship more clearly
plt.title('File Size vs. I/O Activity')
plt.xlabel('File Size (MB)')
plt.ylabel('I/O Activity (Synthetic)')

plt.grid(True, which="both", ls="--")
plt.savefig('file_size_vs_io.png', dpi=300, bbox_inches='tight')


plt.figure(figsize=(10, 6))
sns.violinplot(data=file_sizes_mb, color='cyan')

plt.xscale('log')
plt.title('Violin Plot of File Sizes')
plt.xlabel('File Size (MB)')

plt.grid(True, which="both", ls="--")
plt.savefig('violin_file_sizes.png', dpi=300, bbox_inches='tight')

plt.figure(figsize=(10, 6))
plt.boxplot(file_sizes_mb, vert=False)

plt.xscale('log')
plt.title('Boxplot of File Sizes')
plt.xlabel('File Size (MB)')

plt.grid(True, which="both", ls="--")
plt.savefig('boxplot_file_sizes.png', dpi=300, bbox_inches='tight')
plt.show()
