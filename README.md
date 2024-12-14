# dns-adjuster

This is a poor man's dynamic-DNS docker container. Specifically, it
helps anyone who has DNS configuration in AWS Route53 and needs to
update it every now and then because the IP address of the host it's
pointing to is changing.

## Example
Say, you have a hosted zone configured in Route53 for a domain called
`example.com`. It includes an `A` record for `sub.example.com`,
pointing to the IP address of a server or NAS at your home, say at
`91.32.xxx.yyy`. But your IP address isn't static, and every few
weeks, your provider updates it to a different IP address.

You simple run our docker container:

    docker run -d \
      -e DNS_ADJUSTER_CONFIG="HOSTED_ZONE_ID:sub.example.com" \
      -e DNS_ADJUSTER_LOGPATH="/dns-adjuster/test.log" \
      -e DNS_ADJUSTER_IPFILEPATH="/dns-adjuster/ipfile.txt" \
      -e DNS_ADJUSTER_CRONJOB="0 */2 * * *" \
      -v ~/dns-adjuster:/dns-adjuster \
      -v ~/.aws:/root/.aws \
      dns-adjuster 

(Make sure you replace `HOSTED_ZONE_ID` with the id of your AWS hosted
zone.)

It's a small container that runs a cronjob according to the schedule
you specify, for example above we specified "every two hours". It
checks whether the external-facing IP address of the host it's running
on has changed, and if it has, it updates the DNS record.

We define a docker image that you can use to run a container on any host that 

## AWS Authentication
The container needs access to your AWS credentials. It supports three
methods of AWS authentication in order of preference:

1. IAM Roles (recommended for AWS environments)
   - No configuration needed when running in AWS with proper IAM roles
1. Environment Variables
   ```bash
   -e AWS_ACCESS_KEY_ID=xxx
   -e AWS_SECRET_ACCESS_KEY=xxx
   ```
1. Mounted credentials
    ```bash
    docker run -v ~/.aws:/root/.aws \
         -e DNS_ADJUSTER_CRONJOB="*/5 * * * *" dns-adjuster
    ```

## Volumes
As you noticed in the `docker run` call above, you need to mount a
volume to the container-internal path `/dns-adjuster`. You can mount
any directory of your choice. It must be writable for the docker
user. If you are in an environment with SELinux enabled, you need to
set its context so a docker container can read from it and write to
it:

    chcon -Rt container_file_t /path/to/my/dns-adjuster
    
We recommend creating an a new and empty directory for this purpose,
as the container will create a file in it to store the IP
address. Should you happen to have a name of the same name in the
directory, it would get overriden.

## Environment variables
__`DNS_ADJUSTER_CONFIG`__ This is a vertical-bar (`|`) separated list of
colon-separated pairs. Each pair includes a hosted-zone id and a
domain. For each of the, the dns-adjuster will adjust the `A`-type DNS
record in Route53 to point to the external-facing IP address of the
host the container is running on.

__`DNS_ADJUSTER_LOGPATH`__ If specified, the cronjob will file a log
message to this path each time it checks the IP address. We recommend
using a path inside the `/dns-adjuster` volume that you have to mount
anyway.

__`DNS_ADJUSTER_IPFILEPATH`__ This is where the container will store the
IP address.

__`DNS_ADJUSTER_CRONJOB`__ The cronjob configuration. All hosted zones /
domains will be updated at the same time. They will only be updated if
they did change since the previous check.
