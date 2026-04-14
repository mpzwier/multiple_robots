from setuptools import find_packages, setup

package_name = 'stamped_filter'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/stamped_filter.launch.py']),
        ('share/' + package_name + '/config', ['config/stamped_filter.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='zwier',
    maintainer_email='m.p.zwier@utwente.nl',
    description='TODO: Package description',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'stamped_filter_node = stamped_filter.stamped_filter_node:main'
        ],
    },
)
