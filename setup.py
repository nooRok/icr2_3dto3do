from setuptools import setup, find_packages

setup(
    name='icr2_3dto3do',
    version='0.1.0',
    packages=find_packages(exclude=['tests']),
    url='https://github.com/nooRok/icr2_3dto3do',
    license='MIT',
    author='nooRok',
    author_email='',
    description='N3 *.3d to ICR2 *.3do converter',
    python_requires='>=3.6',
    install_requires=[
        'icr2model @ git+https://github.com/nooRok/icr2model.git@master#egg=icr2model'
    ]
)
