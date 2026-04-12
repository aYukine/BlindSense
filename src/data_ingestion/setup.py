from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'data_ingestion'

# This helper function ensures we only grab FILES, not directories, for data_files
def find_data_files(source_dir, target_dir):
    files = []
    for root, _, filenames in os.walk(source_dir):
        for filename in filenames:
            abspath = os.path.join(root, filename)
            # Calculate the relative path for the install destination
            relpath = os.path.relpath(root, source_dir)
            target_path = os.path.join(target_dir, relpath)
            files.append((target_path, [abspath]))
    return files

data_files = [
    ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
]

# Add all acllite files (including those in lib/ and presenteragent/) safely
data_files += find_data_files('data_ingestion/acllite', os.path.join('share', package_name, 'acllite'))

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=data_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='HwHiAiUser',
    maintainer_email='you@example.com',
    description='Hardware-accelerated video ingestion using NPU DVPP',
    license='TODO: License declaration',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'video_streamer = data_ingestion.video_streamer:main',
            'bag_player = data_ingestion.bag_player:main'
        ],
    },
)