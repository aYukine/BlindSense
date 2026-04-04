from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'camera_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.xml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ayukine',
    maintainer_email='phayuk168@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            "mono_camera_node = camera_pkg.camera:main",
            "show_camera_node = camera_pkg.show_cam:main",
            "mono_camera_compressed_node = camera_pkg.camera_compressed:main",
            "show_camera_compressed_node = camera_pkg.show_cam_compressed:main",
            "stereo_depth = camera_pkg.stereo_depth:main",
            "stereo_perception = camera_pkg.stereo_perception_node:main"
        ],
    },
)