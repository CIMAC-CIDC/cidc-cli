"""Implements """

import click

import api


def upload_assay(assay: str, xlsx_path: str):
    """Upload an assay based on the contents of the metadata .xlsx file located at xlsx_path."""
    try:
        _do_assay_upload(assay, xlsx_path)
    except (Exception, KeyboardInterrupt) as e:

        raise click.ClickException(e)


def _do_assay_upload(assay: str, xlsx_path: str):
    """Actually tries to upload the assay. No error handling here."""

    # Read the .xlsx file and make the API call
    # that initiates the upload job and grants object-level GCS access.
    with open(xlsx, 'rb') as xlsx_file:
        upload_info = api.initiate_upload(assay, xlsx_file)

    click.echo('Initiating upload...')

    # Move to the directory containing the xlsx file,
    # since the local filepaths we get back in upload_info
    # might be relative to that directory.
    xlsx_dir = os.path.abspath(os.path.dirname(xlsx))
    os.chdir(xlsx_dir)

    # Copy the local files into a nested file structure equivalent
    # to the structure we want to create in GCS, rooted in the UPLOAD_WORKSPACE
    # directory. Having the files organized in this manner allows
    # us to upload all files in parallel using the "gsutil -m ..."
    # command below.
    for local_path, gcs_object in upload_info['url_mapping'].items():
        path = os.path.join(UPLOAD_WORKSPACE, gcs_object)
        os.makedirs(path)
        shutil.copy(local_path, path)
    os.chdir(UPLOAD_WORKSPACE)

    # Construct the upload command
    gcs_bucket_uri = 'gs://%s' % upload_info['gcs_bucket']
    gsutil_args = ["gsutil", "-m", "cp", "-r", ".", gcs_bucket_uri]

    # Run the upload command
    subprocess.check_output(gsutil_args)

    # Clean up the workspace
    shutil.rmtree(UPLOAD_WORKSPACE)

    # Alert the API that the upload job failed
    api.job_failed(upload_info['job_id'], upload_info['job_etag'])

    # Alert the user that the upload job failed
    raise e

    # Clean up the workspace
    shutil.rmtree(UPLOAD_WORKSPACE)

    # Alert the API that upload job succeeded
    api.job_succeeded(upload_info['job_id'], upload_info['job_etag'])
