Summary:	Access control list utilities
Name:		acl
Version:	2.2.52
Release:	1%{?dist}
Source0:	http://download.savannah.gnu.org/releases-noredirect/acl/acl-%{version}.src.tar.gz
License:	GPLv2+
Group:		System Environment/Base
URL:		http://acl.bestbits.at/
Vendor:		VMware, Inc.
Distribution:	Photon
Requires:	libacl = %{version}-%{release}
BuildRequires:	attr

%description
This package contains the getfacl and setfacl utilities needed for
manipulating access control lists.

%package -n	libacl
Summary:	Dynamic library for access control list support
License:	LGPLv2+
Group:		System Environment/Libraries
Requires:	attr

%description -n libacl
This package contains the libacl.so dynamic library which contains
the POSIX 1003.1e draft standard 17 functions for manipulating access
control lists.

%package -n	libacl-devel
Summary:	Files needed for building programs with libacl
License:	LGPLv2+
Group:		Development/Libraries
Requires:	libacl = %{version}-%{release}


%description -n libacl-devel
This package contains header files and documentation needed to develop
programs which make use of the access control list programming interface
defined in POSIX 1003.1e draft standard 17.

%prep
%setup -q

%build
%configure

make %{?_smp_mflags} LIBTOOL="libtool --tag=CC"

%check
if ./setfacl/setfacl -m u:`id -u`:rwx .; then
    make tests || exit $?
    if test 0 = `id -u`; then
        make root-tests || exit $?
    fi
else
    echo '*** ACLs are probably not supported by the file system,' \
         'the test-suite will NOT run ***'
fi

%install
make install DESTDIR=%{buildroot}
make install-dev DESTDIR=%{buildroot}
make install-lib DESTDIR=%{buildroot}

find %{buildroot} -name '*.la' -exec rm -f {} ';'

chmod 0755 %{buildroot}%{_libdir}/libacl.so.*.*.*

%find_lang %{name}

%post -n libacl 
/sbin/ldconfig

%postun -n libacl 
/sbin/ldconfig

%files -f %{name}.lang
%{_bindir}/chacl
%{_bindir}/getfacl
%{_bindir}/setfacl
%{_mandir}/man1/chacl.1*
%{_mandir}/man1/getfacl.1*
%{_mandir}/man1/setfacl.1*
%{_mandir}/man5/acl.5*

%files -n libacl-devel
%{_libdir}/libacl.so
%{_includedir}/acl
%{_includedir}/sys/acl.h
%{_mandir}/man3/acl_*
%{_libdir}/libacl.a
%{_datadir}/doc/acl/*   
%{_libexecdir}/libacl.a
%{_libexecdir}/libacl.so
   
%files -n libacl
%{_libdir}/libacl.so.*

%changelog
* Thu Feb 26 2015 Divya Thaluru <dthaluru@vmware.com> 2.2.52-1
- Initial version
