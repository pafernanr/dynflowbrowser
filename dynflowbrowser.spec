Name: dynflowbrowser
Version: 0.0.0
Release: py3
Summary: Interactive browser for analyzing Dynflow task execution data from TheForeman/Red Hat Satellite sosreports.

License: GPLv3
URL:            https://github.com/pafernanr/dynflowbrowser
Source0: https://github.com/pafernanr/%{name}-%{version}.tar.gz
Group: Applications/System
BuildArch: noarch

BuildRoot: %{_tmppath}/%{name}-buildroot
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
Requires: python3-jinja2
Requires: python3-pytz
Requires: python3-pandas
Requires: python3-textual

%description
DynflowBrowser provides two interfaces for analyzing Foreman/Satellite task execution:
- **Terminal Browser**: Fast keyboard-driven TUI for console-based analysis
- **HTTPD Service**: Web interface accessible from any browser

%prep
%setup -qn %{name}-%{version}

%build

%install
rm -rf ${RPM_BUILD_ROOT}

# Set version in __VERSION__ file
echo "v%{version}" > dynflowbrowser/__VERSION__

mkdir -p ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowbrowser/bin
install -D -m 755 dynflowbrowser/bin/__init__.py ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowbrowser/bin/__init__.py
mkdir -p ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowbrowser_export_tasks/bin
install -D -m 755 dynflowbrowser_export_tasks/bin/__init__.py ${RPM_BUILD_ROOT}/usr/lib/tools/dynflowbrowser_export_tasks/bin/__init__.py
cp -rp dynflowbrowser ${RPM_BUILD_ROOT}/usr/lib/tools/
cp -rp dynflowbrowser_export_tasks ${RPM_BUILD_ROOT}/usr/lib/tools/

rm -rf ${RPM_BUILD_ROOT}/usr/lib/tools/%{name}/lib/__pycache__

%post
ln -s -f /usr/lib/tools/dynflowbrowser/bin/__init__.py /usr/bin/dynflowbrowser
ln -s -f /usr/lib/tools/dynflowbrowser_export_tasks/bin/__init__.py /usr/bin/dynflowbrowser-export-tasks

%postun
if [ $1 -eq 0 ] ; then
    rm -f /usr/bin/%{name}
    rm -f /usr/bin/export-tasks
fi

%clean
rm -rf ${RPM_BUILD_ROOT}

%files
%defattr(-,root,root,-)
/usr/lib/tools/dynflowbrowser
/usr/lib/tools/dynflowbrowser_export_tasks
